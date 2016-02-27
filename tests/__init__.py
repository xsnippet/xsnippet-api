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


def inloop(fn):
    """Decorator that runs a wrapped function in the event loop.

    Usage::

        @inloop
        async def test_a(self):
            # test_a is executed in the event loop
            pass

    :param fn: a function to run in the event loop
    :type fn: a function object

    :return: a decorated function
    :rtype: a function object
    """
    @functools.wraps(fn)
    def _wrapper(*args, **kwargs):
        def_loop = asyncio.get_event_loop()
        tmp_loop = asyncio.new_event_loop()

        # set newly created event loop as default one, so we don't need
        # to pass it explicitly down the call stack
        asyncio.set_event_loop(tmp_loop)

        try:
            rv = tmp_loop.run_until_complete(fn(*args, **kwargs))

            # running a given coroutine may produce another ones to free
            # resources (e.g. close sockets) when it's done, so we need
            # to run the event loop one more time to execute them
            tmp_loop.stop()
            tmp_loop.run_forever()
            tmp_loop.close()

        finally:
            asyncio.set_event_loop(def_loop)

        return rv

    return _wrapper


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
    """

    def __new__(mcls, name, bases, namespace):
        for key, value in namespace.items():
            if inspect.iscoroutinefunction(value):
                namespace[key] = inloop(value)

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
        self._loop = app.loop
        self._handler = app.make_handler()
        self._server = None

    async def __aenter__(self):
        if self._server is None:
            self._server = await self._loop.create_server(
                self._handler,
                self._ADDRESS[0],
                self._ADDRESS[1])
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # we've got to wait until client connections are properly closed
        await self._handler.finish_connections()

        self._server.close()
        self._server = None

    async def _http(self, method, url, **kwargs):
        with aiohttp.ClientSession(loop=self._loop) as session:
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
