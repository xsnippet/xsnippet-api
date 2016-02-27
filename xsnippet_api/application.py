"""
    xsnippet_api.application
    ------------------------

    Provides a factory function to create an application instance,
    ready to be served by :function:`aiohttp.web.run_app`.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

from aiohttp import web

from . import database
from . import resources


def create_app(conf, loop=None):
    """Create and return a web application instance.

    The whole point of that function is to provide a way to create
    an application instance using some external context such as
    settings or event loop to run in.

    :param conf: a settings to be used to create an application instance
    :type conf: :class:`dict`

    :param loop: an event loop to run in
    :type loop: :class:`asyncio.BaseEventLoop` or None

    :return: an application instance
    :rtype: :class:`aiohttp.web.Application`
    """
    app = web.Application(loop=loop)

    app.router.add_route(
        '*', '/snippets', resources.Snippets, name='snippets')

    # attach settings to the application instance in order to make them
    # accessible at any point of execution (e.g. request handling)
    app['conf'] = conf
    app['db'] = database.create_connection(conf, loop=loop)

    return app
