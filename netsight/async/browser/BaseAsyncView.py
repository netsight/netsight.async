from collections import Mapping
from copy import deepcopy
from cStringIO import StringIO
import threading
import types
import uuid

from persistent.dict import PersistentDict
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
import transaction
from zope.i18n import translate
from zope.i18nmessageid import MessageFactory
from zope.publisher.interfaces.http import IHTTPResponse
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.Publish import publish, mapply

try:
    import json
except ImportError:
    import simplejson as json
    
from netsight.async.registry import getProcessRegistry

uid_generator = lambda: uuid.uuid4().hex
_ = MessageFactory('netsight.async')


def is_numeric(n):
    return isinstance(n, (types.LongType, types.IntType, types.FloatType)) and \
           not isinstance(n, types.BooleanType)


class NoSuchProcessError(RuntimeError):
    """ The process is in another castle.
    """
    
    pass


class ThreadDiedBeforeCompletionError(RuntimeError):
    """ 
    """
    
    pass

            
def process_wrapper(pid, request_body, request_environ):
    # Sets up everything we need to run a view method in a new Zope-ish
    # context, then runs it and stores the result for later retrieval.
    
    _process = None

    def my_mapply(object, positional=(), keyword={},
                   debug=None, maybe=None,
                   missing_name=None,
                   handle_class=None,
                   context=None, bind=0):
        
        if not isinstance(keyword, Mapping):
            keyword = {}
        keyword['process_id'] = pid
        
        args = (getattr(object, '__run__', object),)
        kwargs = dict(positional=positional,
                      keyword=keyword,
                      debug=debug,
                      maybe=maybe,
                      context=context,
                      bind=bind
                      )
        if missing_name is not None:
            kwargs['missing_name'] = missing_name
        if handle_class is not None:
            kwargs['handle_class'] = handle_class
        return mapply(*args, **kwargs)
        
    response = HTTPResponse(stdout=StringIO(), stderr=StringIO())
    request = HTTPRequest(StringIO(request_body), request_environ, response)
    
    request.set('process_id', pid)
    
    import Zope2
    app = Zope2.bobo_application.__bobo_traverse__(request)
    reg = getProcessRegistry(app)
    _process = reg.get(pid)
    
    
    # Run
    try:
        try:
            response = publish(request, 'Zope2', [None], mapply=my_mapply)
            
            # We can't just pass the response back, as the data streams will not
            # be set up right.
            attr = (hasattr(response, 'cookies') and 'cookies') or \
                   (hasattr(response, '_cookies') and '_cookies')
            cookies = deepcopy(getattr(response, attr))
            
            if IHTTPResponse.providedBy(response):
                _process['result'] = (response.getStatus(),
                                      dict(response.getHeaders()),
                                      cookies,
                                      response.consumeBody())
            else:
                # Currently, ZPublisher.HTTPResponse doesn't implement
                # IHTTPResponse, even though HTTPRequest implements
                # IHTTPRequest.
                _process['result'] = (response.getStatus(),
                                      dict(response.headers),
                                      cookies,
                                      response.body)
                
        except Exception, e:
            # Set result to the exception raised
            _process['result'] = e
            raise
        else:
            # Set completed
            completed = _process.get('completed')
            if is_numeric(completed):
                completed = 100
            else:
                completed = True
            _process['completed'] = completed
            transaction.commit()
    finally:
        # Clean up our extra thread.
        request.close()


class BaseAsyncView(BrowserView):
    """ A base view for a long-running process. Override the
        __run__ method to process data on POST. The result method
        will yield None until completed returns True, when it
        will yield the result returned by _run.
    """
    
    initial_page = None
    processing_page = ViewPageTemplateFile('templates/processing.pt')
    
    def run_process(self):
        # Returns True if the current request should trigger the
        # __run__ method to be kicked off.
        return self.request.get('REQUEST_METHOD')=='POST'
    
    def _run(self):
        # Internal function to kick off the asynchronous process.
            
        process_id = uid_generator()
        
        # Copy the request: hasattrs for differentiating between
        # zope.publisher and ZPublisher HTTPRequests.
        if hasattr(self.context.REQUEST, 'environ'):
            request_environ = deepcopy(self.context.REQUEST.environ)
        elif hasattr(self.context.REQUEST, '_environ'):
            request_environ = deepcopy(self.context.REQUEST._environ)
        else:
            request_environ = {}
        if hasattr(self.context.REQUEST, 'stdin'):
            self.context.REQUEST.stdin.seek(0)
            request_body = self.context.REQUEST.stdin.read()
        elif hasattr(self.context.REQUEST, 'bodyStream'):
            self.context.REQUEST.bodyStream.stream.seek(0)
            request_body = self.context.REQUEST.bodyStream.stream.read()
        else:
            request_body = ''
        
        # Pass as little from the current thread to the new thread as
        # possible. Too easy to get lost in ZODB & transaction hell
        # otherwise. Nothing with 'context' or a connection should go
        # through. Function is outside of this class to avoid scope
        # mix-up.
        setup = {'request_environ': request_environ,
                 'request_body': request_body,
                 'pid': process_id}
                
        name = '<%s>' % (process_id)
        
        # We start a new thread outside of the normal Zope limits,
        # naughty but necessary for now.
        t = threading.Thread(target=process_wrapper, name=name, kwargs=setup)
        
        getProcessRegistry(self.context)[process_id] = PersistentDict({'completed': False,
                                                                       'result': None})
        # Ensure we have committed in this thread before the spawned
        # thread tries to retrieve the process record.
        transaction.commit()
        
        t.start()
        
        return process_id
    
    def __run__(self, process_id=None, *args, **kwargs):
        """ Override this method in your subclass.
        """
        
        raise NotImplementedError
    
    def _get_process(self, process_id):
        # Internal function, used to raise an error if a process with
        # the given ID doesn't exist.

        process = getProcessRegistry(self.context).get(process_id)
        if not process:
            raise NoSuchProcessError
        return process
    
    def set_progress(self, process_id, percentage):
        # To be called by the running process to set its completion
        # process as a number between 0 and 100.
        
        process = self._get_process(process_id)
        process['completed'] = round(percentage, 1)
        if process['completed'] % 1 == 0:
            process['completed'] = int(process['completed'])
    
    def processing(self, process_id):
        """ If the process is completed, redirects to the completed
            result. Otherwise shows the processing page.
        """
        completed = self.completed(process_id)
        
        if completed is True or completed==100:
            completed_uri = '%s/%s/result?process_id=%s' % \
                            (self.context.absolute_url(),
                             self.__name__,
                             process_id)
            return self.request.response.redirect(completed_uri)
        else:
            return self.processing_page(process_id=process_id)
    
    def completed(self, process_id, output_json=False):
        """ Return some measure of completeness. If your _run method
            informs of some percentage completeness via the
            _set_progress method, returns a number between 0 and 100,
            otherwise returns False or True.
        """
        
        if output_json:
            self.context.REQUEST.RESPONSE.setHeader('Content-Type', 'application/json')
        
        try:
            process = self._get_process(process_id)
        except NoSuchProcessError:
            if output_json:
                return json.dumps({'completed': 'ERROR'})
            else:
                raise
            
        completed = process.get('completed', None)
        result = process.get('result')
        if isinstance(result, Exception) and \
           completed is not True and \
           completed != 100:
            exception = result
            if not output_json:
                del getProcessRegistry(self.context)[process_id]
                raise ThreadDiedBeforeCompletionError(exception)
            else:
                return json.dumps({'completed': 'ERROR'})
        
        if not output_json:
            return completed
        else:
            if hasattr(self.context, 'portal_languages'):
                lang = self.context.portal_languages.getPreferredLanguage()
            else:
                lang = 'en' 
            progress_message = _(u'percentage_completion',
                                 u'${percentage}% completed...',
                                 mapping={'percentage': completed or 0})
            return json.dumps({'completed': completed,
                               'progress_message': translate(progress_message,
                                                             target_language=lang)})
    
    def result(self, process_id):
        """ Get the result of the given process. If the process has not
            completed, returns None. Once the result has been
            successfully fetched, it cannot be fetched again.
        """
        process = self._get_process(process_id)
        response_details = process.get('result')
        
        completed = None
        try:
            try:
                completed = self.completed(process_id)
            except ThreadDiedBeforeCompletionError:
                completed = 100
                raise
        finally:
            if completed is True or completed == 100:
                del getProcessRegistry(self.context)[process_id]
        
        if response_details:
            response = self.request.response
            
            status, headers, cookies, body = response_details
            response.setStatus(status)
            
            # Overwriting headers/cookies here is a bit crude, I have
            # tried to use declared interface methods wherever possible
            # but there are some omissions that have to be worked
            # around.
            
            # Currently, ZPublisher.HTTPResponse doesn't implement
            # IHTTPResponse, even though HTTPRequest implements
            # IHTTPRequest.
            current_headers = getattr(response, 'headers',
                              getattr(response, '_headers',
                              {}))
            result_headers = dict([(k.lower(), v) for k, v in headers.items()])
            for h in set(current_headers.keys() + result_headers.keys()):
                if h not in headers and h in current_headers:
                    # no interface-friendly way to unset headers anyway.
                    del current_headers[h]
                else:
                    response.setHeader(h, result_headers[h])
            
            # no interface-friendly way to enumerate response cookies
            # or unset cookies.
            attr = (hasattr(response, 'cookies') and 'cookies') or \
                   (hasattr(response, '_cookies') and '_cookies')
            setattr(response, attr, cookies)
            
            if IHTTPResponse.providedBy(response):
                response.setResult(body)
            else:
                response.setBody(body)
            
            return response
        
        else:
            return None
    
    def publishTraverse(self, request, name):
        if name in ('completed', 'processing', 'result'):
            return getattr(self, name)
        
        return self
    
    def __call__(self, REQUEST=None, no_process=False, *args, **kwargs):
        """ If the request method is POST, kick off the process and
            show the processing page. Otherwise, show the initial page.
        """
        
        REQUEST = REQUEST or self.request
        
        if self.run_process() and not no_process:
            
            process_id = self._run()
            
            processing_uri = '%s/%s/processing?process_id=%s' % \
                             (self.context.absolute_url(),
                              self.__name__,
                              process_id)
                             
            return REQUEST.response.redirect(processing_uri)
        
        if self.initial_page:
            return self.initial_page(*args, **kwargs)
        
        return super(BaseAsyncView, self).__call__(REQUEST=REQUEST, *args, **kwargs)