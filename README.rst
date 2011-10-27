==============
netsight.async
==============

Introduction
============

netsight.async provides a base browser view for the Zope Web Framework
which enables browser requests to run in the background whilst progress
of the request is returned to the browser.

Usage
=====

Basic
-----

First, subclass the ``BaseAsyncView`` class. Where you might ordinarily
write code in the ``__call__`` method of a view class, to perform some
process, instead, place it in the ``__run__`` method. ::

    >>> import time
    >>> from netsight.async.browser.BaseAsyncView import BaseAsyncView
    >>> class MyView(BaseAsyncView):
    ...    
    ...    def __run__(self, *args, **kwargs):
    ...         time.sleep(30)
    ...         return "Hello world!"
    ...
    >>>
    
When you call this view from the browser, it will display whatever
output is configured as normal. When you perform a POST request to the
view, however, the ``__run__`` method will be called in the background
as if it were the ``__call__`` method of the view class. Meanwhile, a
page displaying a spinner will be returned to the browser and will poll
at 5 second intervals until the process defined in ``__run__``
completes.

Once the ``__run__`` method has completed, the browser will redirect to
the result.

Example timeline:
~~~~~~~~~~~~~~~~~

 1. User visits '/myview' and is shown some form.
 
 2. User submits the form, the process is started in the background.
 
 3. The user is redirected to
    '/myview/processing?process_id=abcde-f01234' which shows a spinner.
    
 4. The user's current page polls for process status for up to 30
    seconds via AJAX if possible, otherwise by page refresh.
    
 5. Once the process has completed, the user is redirected to
    '/myview/result?process_id=abcde-f01234' and shown "Hello world!"

Using with page templates
-------------------------

If you have configured a browser view for your view class with a
page template file specified in ZCML, this will be shown by default
when the view is first called. If the view is POSTed to, then the
process will be kick-started. You can change the initial template and
the conditions under which the process is started by overriding the
``initial_page`` and the ``run_process`` methods of the view. ::

    >>> from Products.Five.browser.pagetemplatefile import \
    ...      ViewPageTemplateFile
    >>>
    >>> class MyView(BaseAsyncView):
    ...     
    ...     def run_process(self):
    ...         return 'run' in self.request.form
    ...     
    ...     initial_page = \
    ...         ViewPageTemplateFile('templates/my_template.pt')
    ...
    >>>
    
Or you could use a method::

    >>> class MyView(BaseAsyncView):
    ...     
    ...     def initial_page(self, *args, **kwargs):
    ...         return 'Hello world!'
    ...
    >>>
    
You can also override the page returned to the browser once the process
has been started by overriding the processing_page method.

If you want to call a template defined in ZCML from your ``__run__``
method, you may pass a ``True`` value named ``no_process` to the call
method if your ``run_process`` method would ordinarily start the
process again. ::

    >>> class MyView(BaseAsyncView):
    ...     
    ...     def __run__(self, *args, **kwargs):
    ...         return self.__call__(message="Hello world",
    ...                              no_process=True)
    ...
    >>>


Checking the status & retrieving the result
-------------------------------------------

Once you have kicked off your ``__run__`` method,  the resulting
response will redirect to the processing view, with a unique ID for the
newly started process given as a GET variable, ``process_id``.

This process ID can be used to retrieve information on the status of
the process and its result.

Calling the ``completed`` method of the view with the process ID will
return either a ``True`` or ``False`` completion state, or a number
representing a percentage completion out of 100 (more on recording
progress later). If the optional argument, ``output_json`` is set to
some value which evaluates to ``True``, the method returns a JSON
object with the single key, ``completed`` containing the same ``True``,
``False`` or numeric value.

If your process died before it completed, it will raise an error, or if
JSON output is chosen, it will return a ``completed`` value of the
string, 'ERROR'.

To retrieve the result of the ``__run__`` method once it has completed,
call the ``result`` method of the view with the process ID.

If your process died before it completed, this too will raise an error,
or if JSON output is chosen, it will return a ``completed`` value of
the string, 'ERROR'.

If the process has not yet completed when ``result`` is called,
``None`` will be returned.

Setting process progress from your task
---------------------------------------

If you want your task to return some measure of completion you can call
the ``set_progress`` method with the process ID and some numeric value.
::

    >>> class MyView(BaseAsyncView):
    ...    
    ...    def __run__(self, process_id=None, *args, **kwargs):
    ...         time.sleep(15)
    ...         self.set_progress(process_id, 50)
    ...         time.sleep(15)
    ...         return "Hello world!"
    ...
    >>>
    
When your task completes without raising an exception, the progress is
automatically set to 100 so there is no need to set this before the
method returns.

Installation
============

Simply add ``netsight.async`` to the ``eggs`` section of your buildout
configuration. If you also plan on using the stock 'processing' page,
you may also need to add it to the ``zcml`` section. ::

  [buildout]
  eggs = ...
         netsight.async
  zcml = ...
         netsight.async

Limitations
===========

Because running the new process cannot be done using existing threads
from the Zope pool, for the duration of the asynchronous process, an
extra thread is created by the Zope process, beyond the normal thread
limit. This also means an extra connection is opened to the ZODB beyond
the normal connection limit which may cause a warning to be shown in
either the console or log files.

Once the ``__run__`` method has started, it cannot be stopped by the
user in any way. This a feature that subclasses may implement if
they choose, but would be dangerous to implement in this package
without knowledge of what the background task was doing & what cleanup
may be required.

To be improved
==============

Currently processes are stored in memory of a particular Python
instance. This introduces the following issues:

 * If the user never retrieves the results from the ``__run__``
   method, they are stored in the ZODB permanently.

Dependencies
============

 * Python>=2.4.0

 * zope.component>=3.4.0
 
 * zope.i18n>=3.4.0
 
 * zope.i18nmessageid>=3.4.0
 
 * zope.publisher
 
 * Zope>=2.8.0
 
The default processing page template depends on a main template being,
provided, much like the one provided by Products.CMFPlone, however
this may be overridden by your own view, as discussed above.

Contributions
=============

You can find the source code for this project at:

  http://github.com/netsight/netsight.async

This product needs translations! There are only 2 strings to do, so
this is a really quick and easy way to contribute to an open-source
project.

Any bug fixes, new features & documentation improvements are welcome,
just submit a pull request on github.