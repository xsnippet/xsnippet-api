"""
    xsnippet_api.application
    ------------------------

    Provides a factory function to create an application instance,
    ready to be served by :function:`aiohttp.web.run_app`.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

from aiohttp import web, web_urldispatcher

from . import database, resources, router


def create_app(conf):
    """Create and return a web application instance.

    The whole point of that function is to provide a way to create
    a full-featured application instance with database sesstion,
    routes and so on.

    :param conf: a settings to be used to create an application instance
    :type conf: :class:`dict`

    :return: an application instance
    :rtype: :class:`aiohttp.web.Application`
    """
    router_v1 = web_urldispatcher.UrlDispatcher()
    router_v1.add_route('*', '/snippets', resources.Snippets)
    router_v1.add_route('*', '/snippets/{id}', resources.Snippet)

    app = web.Application(router=router.VersionRouter(
        {
            '1': router_v1,
        }
    ))

    # attach settings to the application instance in order to make them
    # accessible at any point of execution (e.g. request handling)
    app['conf'] = conf
    app['db'] = database.create_connection(conf)

    return app
