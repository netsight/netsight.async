import re
import time

import mock
from zope.publisher.browser import TestRequest

from netsight.async.browser.tests.base import BaseTestCase


class TestAsyncView(BaseTestCase):
    
    def afterSetUp(self):
        
        from netsight.async.browser.BaseAsyncView import BaseAsyncView
        
        class MyProcessView(BaseAsyncView):
            
            initial_page = lambda x=None: 'foo'
            
            def __init__(self, context, request):
                self.context = context
                self.request = request
                self.__name__ = 'my_process_view'
                
            def __run__(self, *args, **kwargs):
                time.sleep(3)
                return 1
        
        class MyProcessViewWithProgress(MyProcessView):
                
            def __run__(self, process_id=None, *args, **kwargs):
                self.set_progress(process_id, 0)
                time.sleep(3)
                self.set_progress(process_id, 55)
                time.sleep(3)
                return 1
                
        self.context = self.getPortal()
        self.request = TestRequest(environ=dict(SERVER_URL='http://nohost',
                                                HTTP_HOST='nohost'))
        self.request.method = "POST"
        self.request._environ['REQUEST_METHOD'] = 'POST'
        
        self.view = MyProcessView(self.context, self.request)
        processing_page = lambda **options: '<h1>Processing...</h1>%s%%' % \
                                            (self.view.completed(
                                                 options.get('process_id')),
                                             )
        self.view.processing_page = processing_page
        self.progress_view = MyProcessViewWithProgress(self.context, self.request)
        self.progress_view.processing_page = processing_page
        
        from netsight.async.browser import BaseAsyncView as view_module
        view_module.super = mock.Mock()
        
    def beforeTearDown(self):
        from netsight.async.browser import BaseAsyncView
        del BaseAsyncView.super
        
    def test_process_view_get(self):
                
        self.request.method = "GET"
        self.request._environ['REQUEST_METHOD'] = 'GET'
        
        self.assertEqual(self.view(), 'foo')
        
        self.view.initial_page = None
        
        self.assertEqual(self.view(), processview.super().__call__()) #@UndefinedVariable
        
    def test_process_view_post(self):
        
        from netsight.async.browser.BaseAsyncView import NoSuchProcessError
        
        result = self.view()
        
        # Test we were redirected to the processing page
        redirect_uri = result
        
        processing_uri = '%s/my_process_view/processing\?process_id=(.+)' % \
                          (self.context.absolute_url(),)
        self.assertNotEqual(re.match(processing_uri, redirect_uri), None, "%s did not match %s" % (redirect_uri, processing_uri))
        
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
        self.assertNotEqual(re.match(completed_uri, redirect_uri), None, "%s did not match %s" % (redirect_uri, completed_uri))
        completed_process_id = re.match(completed_uri, redirect_uri).group(1)
        self.assertEqual(completed_process_id, process_id)
        
        # Test result
        self.assertEqual(self.view.result(process_id), 1)
        
        # Test process removed after result fetched
        self.assertRaises(NoSuchProcessError, self.view.result, process_id)
        
    def test_process_view_post_with_progress(self):
        
        from netsight.async.browser.BaseAsyncView import NoSuchProcessError
        
        redirect_uri = self.progress_view()
        
        processing_uri = '%s/my_process_view/processing\?process_id=(.+)' % \
                          (self.context.absolute_url(),)
        self.assertNotEqual(re.match(processing_uri, redirect_uri), None, "%s did not match %s" % (redirect_uri, processing_uri))
        
        process_id = re.match(processing_uri, redirect_uri).group(1)
        
        # Give it time to get started
        time.sleep(0.5)
        
        # Run hasn't completed immediately
        self.assertEqual(self.progress_view.completed(process_id), 0)
        
        # Result is None until completion
        self.assertEqual(self.progress_view.result(process_id), None)
        
        # Processing page has the correct content & doesn't try to
        # redirect to the result.
        processing = self.progress_view.processing(process_id)
        self.assertTrue('<h1>Processing...</h1>' in \
                        processing)
        self.assertTrue('0%' in \
                        processing, "Expected 0%% in '%s'" % (processing,))
        
        # Give it time to get to stage 1
        time.sleep(3)
        
        # Test completion flag set
        self.assertEqual(self.progress_view.completed(process_id), 55)
        
        # Result is None until completion
        self.assertEqual(self.progress_view.result(process_id), None)
        
        # Processing page has the correct content & doesn't try to
        # redirect to the result.
        processing = self.progress_view.processing(process_id)
        self.assertTrue('<h1>Processing...</h1>' in \
                        processing, "Expected '<h1>Processing...</h1>' in '%s'" % (processing,))
        self.assertTrue('55%' in \
                        processing, "Expected '55%%' in '%s'" % (processing,))
        
        # Give it time to complete
        time.sleep(4)
        
        # Test completion flag set
        self.assertEqual(self.progress_view.completed(process_id), 100)
        
        # Test processing redirects after completion
        redirect_uri = self.progress_view.processing(process_id)
        completed_uri = '%s/my_process_view/result\?process_id=(.+)' %\
                               (self.context.absolute_url(),)
        self.assertNotEqual(re.match(completed_uri, redirect_uri), None, "%s did not match %s" % (redirect_uri, processing_uri))
        completed_process_id = re.match(completed_uri, redirect_uri).group(1)
        self.assertEqual(completed_process_id, process_id)
        
        # Test result
        self.assertEqual(self.progress_view.result(process_id), 1)
        
        # Test process removed after result fetched
        self.assertRaises(NoSuchProcessError, self.progress_view.result, process_id)