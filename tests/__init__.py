"""
    tests
    -----

    Tests XSnippet API. Except that it provides useful testing facilities
    that one day might be considered to be moved into separate library.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import asyncio
import functools
import inspect

import aiohttp


def inloop(fn=None, *, setup=None, teardown=None):
    """Decorator that runs a wrapped function in the event loop.

    Usage::

        @inloop
        async def test_a(self):
            # test_a is executed in the event loop
            pass

        @inloop(setup=spam, teardown=eggs)
        async def test_b(self):
            # test_b is executed in the event loop after spam was successfully
            # executed. When test_b returns, eggs will be executed
            pass

    :param fn: a function to run in the event loop
    :type fn: a function object

    :param setup: a callable to be executed *before* the function. Can also be
                  a coroutine object, in which case it will be executed in the
                  context of the created event loop
    :type setup: a callable object

    :param teardown: a callable object to be executed *after* the function. Can
                     also be a coroutine object, in which case it will be
                     executed in the context of the created event loop
    :type teardown: a callable object

    :return: a decorated function
    :rtype: a function object

    """

    def decorate(fn):
        @functools.wraps(fn)
        def _wrapper(self, *args, **kwargs):
            def_loop = asyncio.get_event_loop()
            tmp_loop = asyncio.new_event_loop()

            # set newly created event loop as default one, so we don't need
            # to pass it explicitly down the call stack
            asyncio.set_event_loop(tmp_loop)

            if setup:
                if inspect.iscoroutinefunction(setup):
                    tmp_loop.run_until_complete(setup(self))
                else:
                    setup(self)

            try:
                try:
                    rv = tmp_loop.run_until_complete(fn(self, *args, **kwargs))
                finally:
                    if teardown:
                        if inspect.iscoroutinefunction(teardown):
                            tmp_loop.run_until_complete(teardown(self))
                        else:
                            teardown(self)

                if not tmp_loop.is_closed():
                    # running coroutines may produce another ones to free
                    # resources, so we need to stop accepting new ones
                    # and run the loop until everything is done.
                    tmp_loop.call_soon(tmp_loop.stop)
                    tmp_loop.run_forever()
                    tmp_loop.close()

            finally:
                asyncio.set_event_loop(def_loop)

            return rv

        return _wrapper

    if fn:
        return decorate(fn)
    else:
        return decorate


class AIOTestMeta(type):
    """Metaclass for testing async functions.

    Use this metaclass when you need to test async functions / methods
    and you don't want to explicitly write running code for coroutines
    in each test case.

    Usage::

        class TestSnippets(unittest.TestCase, metaclass=AIOTestMeta):

            async def test_a(self):
                self.assertEqual(42, await my_coro())

            def test_b(self):
                self.assertEqual(42, my_fn())

    Regular test cases will be run in usual way, while async ones - inside
    event loop.

    A test class may contain special setup / teardown methods, which will
    be executed before and after running of each test case::

        class TestSnippets(unittest.TestCase, metaclass=AIOTestMeta):

            def setup(self):
                self.app = create_app(DEFAULT_CONF)

            def teardown(self):
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.app['db'].snippets.drop())

            async def test_a(self):
                self.assertEqual(42, await my_coro())

    Both setup and teardown can also be coroutine methods, in which case they
    will automatically be executed in the context of a created event loop::

         class TestSnippets(unittest.TestCase, metaclass=AIOTestMeta):

            def setup(self):
                self.app = create_app(DEFAULT_CONF)

            async def teardown(self):
                await self.app['db'].snippets.drop()

            async def test_a(self):
                self.assertEqual(42, await my_coro())

    """

    def __new__(mcls, name, bases, namespace):
        setup = namespace.pop('setup', None)
        teardown = namespace.pop('teardown', None)

        for key, value in namespace.items():
            if inspect.iscoroutinefunction(value):
                namespace[key] = inloop(setup=setup, teardown=teardown)(value)

        return super(AIOTestMeta, mcls).__new__(mcls, name, bases, namespace)


class AIOTestApp(object):
    """Facade to test an :class:`aiohttp.web.Application` instance.

    The facade runs a passed application instance in local server, and
    provides convenient methods to make HTTP requests.

    Usage::

        async with AIOTestApp(app) as app:
            resp = await app.get('/endpoint')

    :param app: an application instance
    :type app: :class:`aiohttp.web.Application`
    """

    _ADDRESS = ('127.0.0.1', 0)

    def __init__(self, app):
        self._app = app
        self._handler = None
        self._server = None

    async def __aenter__(self):
        await self._app.startup()
        self._handler = self._app.make_handler()

        if self._server is None:
            self._server = await self._app.loop.create_server(
                self._handler,
                self._ADDRESS[0],
                self._ADDRESS[1])
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._server.close()
        await self._server.wait_closed()

        # we've got to wait until client connections are properly closed
        await self._app.shutdown()
        await self._handler.shutdown()
        await self._app.cleanup()

        self._server = None
        self._handler = None

    async def _http(self, method, url, **kwargs):
        with aiohttp.ClientSession(loop=self._app.loop) as session:
            method = getattr(session, method)
            return await method(self._resolve(url), **kwargs)

    post = functools.partialmethod(_http, 'post')
    put = functools.partialmethod(_http, 'put')
    patch = functools.partialmethod(_http, 'patch')
    get = functools.partialmethod(_http, 'get')
    delete = functools.partialmethod(_http, 'delete')

    def _resolve(self, url):
        resource = url[1:] if url.startswith('/') else url
        address, port = self._server.sockets[0].getsockname()
        return 'http://{0}:{1}/{2}'.format(address, port, resource)
