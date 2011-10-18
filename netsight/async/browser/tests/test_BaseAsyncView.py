from cStringIO import StringIO
import re
import time

import mock
from zope.publisher.browser import TestRequest

from netsight.async.browser.tests.base import BaseTestCase


class TestAsyncView(BaseTestCase):
    
    def afterSetUp(self):
        
        from netsight.async.browser.BaseAsyncView import BaseAsyncView
        
        class MyAsyncView(BaseAsyncView):
            
            initial_page = lambda x=None: 'foo'
            
            def __init__(self, context, request):
                self.context = context
                self.request = request
                self.__name__ = 'my_process_view'
                
            def __run__(self, *args, **kwargs):
                time.sleep(3)
                return '1'
        
        class MyAsyncViewWithProgress(MyAsyncView):
                
            def __run__(self, process_id=None, *args, **kwargs):
                self.set_progress(process_id, 0)
                time.sleep(3)
                self.set_progress(process_id, 55)
                time.sleep(3)
                return '1'
                
        self.context = self.getPortal()
        self.request = TestRequest(body_instream=StringIO(),
                                   environ=dict(SERVER_URL='http://nohost',
                                                HTTP_HOST='nohost'))
        self.context.REQUEST = self.request
        
        self.request.method = "POST"
        self.request._environ['REQUEST_METHOD'] = 'POST'
        
        self.view = MyAsyncView(self.context, self.request)
        
        def processing_page(**options):
            completed = self.view.completed(options.get('process_id'))
            if completed is not True and completed is not False:
                return '<h1>Processing...</h1>%s%%' % (completed,)
            else:
                return '<h1>Processing...</h1>'
            
        self.view.processing_page = processing_page
        self.progress_view = MyAsyncViewWithProgress(self.context,
                                                     self.request)
        self.progress_view.processing_page = processing_page
        
        def test_publish(request, *args, **kwargs):
            response = mock.Mock()
            response.getStatus.return_value = 200
            response.headers = {}
            response.cookies = {}
            process_id = request.get('process_id')
            result = self.view.__run__(process_id=process_id)
            response.consumeBody.return_value = result
            response.body = result
            return response
        
        from netsight.async.browser import BaseAsyncView as view_module
        view_module.super = mock.Mock()
        self._publish = view_module.publish
        view_module.publish = test_publish
        
    def beforeTearDown(self):
        from netsight.async.browser import BaseAsyncView as view_module
        del view_module.super
        view_module.publish = self._publish
        
    def test_process_view_get(self):
        from netsight.async.browser import BaseAsyncView
                
        self.request.method = "GET"
        self.request._environ['REQUEST_METHOD'] = 'GET'
        
        self.assertEqual(self.view(), 'foo')
        
        self.view.initial_page = None
        
        self.assertEqual(self.view(),
                         BaseAsyncView.super().__call__()) #@UndefinedVariable
        
    def test_process_view_post(self):
        
        from netsight.async.browser.BaseAsyncView import NoSuchProcessError
        
        result = self.view()
        
        # Test we were redirected to the processing page
        redirect_uri = result
        
        processing_uri = '%s/my_process_view/processing\?process_id=(.+)' % \
                          (self.context.absolute_url(),)
        self.assertNotEqual(re.match(processing_uri, redirect_uri), None)
        
        process_id = re.match(processing_uri, redirect_uri).group(1)
        
        # Run hasn't completed immediately
        self.assertEqual(self.view.completed(process_id), False)
        
        # Result is None until completion
        self.assertEqual(self.view.result(process_id), None)
        
        # Processing page has the correct content & doesn't try to
        # redirect to the result.
        self.assertTrue('<h1>Processing...</h1>' in \
                        self.view.processing(process_id))
        
        # Give it time to complete
        time.sleep(4)
        
        # Test completion flag set
        self.assertEqual(self.view.completed(process_id), True)
        
        # Test processing redirects after completion
        redirect_uri = self.view.processing(process_id)
        completed_uri = '%s/my_process_view/result\?process_id=(.+)' %\
                               (self.context.absolute_url(),)
        self.assertNotEqual(re.match(completed_uri, redirect_uri), None)
        completed_process_id = re.match(completed_uri, redirect_uri).group(1)
        self.assertEqual(completed_process_id, process_id)
        
        # Test result
        self.assertEqual(self.view.result(process_id).consumeBody(), '1')
        
        # Test process removed after result fetched
        self.assertRaises(NoSuchProcessError, self.view.result, process_id)
        
    def test_process_view_post_with_progress(self):
        
        from netsight.async.browser.BaseAsyncView import NoSuchProcessError
        
        self.view = self.progress_view
        redirect_uri = self.view()
        
        processing_uri = '%s/my_process_view/processing\?process_id=(.+)' % \
                          (self.context.absolute_url(),)
        self.assertNotEqual(re.match(processing_uri, redirect_uri), None)
        
        process_id = re.match(processing_uri, redirect_uri).group(1)
        # Give it time to get started
        time.sleep(0.5)
        
        # Run hasn't completed immediately
        self.assertEqual(self.view.completed(process_id), 0)
        
        # Result is None until completion
        self.assertEqual(self.view.result(process_id), None)
        
        # Processing page has the correct content & doesn't try to
        # redirect to the result.
        processing = self.view.processing(process_id)
        self.assertTrue('<h1>Processing...</h1>' in \
                        processing)
        self.assertTrue('0%' in \
                        processing, "Expected 0%% in '%s'" % (processing,))
        
        # Give it time to get to stage 1
        time.sleep(3)
        
        # Test completion flag set
        self.assertEqual(self.view.completed(process_id), 55)
        
        # Result is None until completion
        self.assertEqual(self.view.result(process_id), None)
        
        # Processing page has the correct content & doesn't try to
        # redirect to the result.
        processing = self.view.processing(process_id)
        self.assertTrue('<h1>Processing...</h1>' in \
                        processing,
                        "Expected '<h1>Processing...</h1>' in '%s'" % (processing,))
        self.assertTrue('55%' in \
                        processing, "Expected '55%%' in '%s'" % (processing,))
        
        # Give it time to complete
        time.sleep(4)
        
        # Test completion flag set
        self.assertEqual(self.view.completed(process_id), 100)
        
        # Test processing redirects after completion
        redirect_uri = self.view.processing(process_id)
        completed_uri = '%s/my_process_view/result\?process_id=(.+)' %\
                               (self.context.absolute_url(),)
        self.assertNotEqual(re.match(completed_uri, redirect_uri), None, "%s did not match %s" % (redirect_uri, processing_uri))
        completed_process_id = re.match(completed_uri, redirect_uri).group(1)
        self.assertEqual(completed_process_id, process_id)
        
        # Test result
        self.assertEqual(self.view.result(process_id).consumeBody(), '1')
        
        # Test process removed after result fetched
        self.assertRaises(NoSuchProcessError, self.view.result, process_id)