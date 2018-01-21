"""
    xsnippet.api.application
    ------------------------

    Provides a factory function to create an application instance,
    ready to be served by :function:`aiohttp.web.run_app`.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import aiohttp.web

from . import database, router, middlewares, resources


def _inject_vary_header(request, response):
    """Inject a ``Vary`` HTTP header to response if needed.

    Depends on whether request has varies HTTP headers or not, we may or may
    not inject a ``Vary`` HTTP header into response. Since XSnippet API
    implements content negotiation and API versioning, we've got to pass at
    least ``Accept`` and ``Api-Version`` HTTP headers.

    :param request: an http request instance
    :type request: :class:`~aiohttp.web.Request`

    :param response: an http response instance
    :type response: :class:`~aiohttp.web.Response`
    """
    known = set([
        'Accept',
        'Accept-Encoding',
        'Api-Version',
    ])
    found = [header for header in known if header in request.headers]

    if found:
        response.headers['Vary'] = ', '.join(found)


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

    v1 = aiohttp.web.UrlDispatcher()
    v1.add_route('*', '/snippets', resources.Snippets)
    v1.add_route('*', '/snippets/{id}', resources.Snippet)
    v1.add_route('*', '/syntaxes', resources.Syntaxes)

    # We need to import all the resources in order to evaluate @endpoint
    # decorator, so they can be collected and passed to VersionRouter.
    app = aiohttp.web.Application(
        middlewares=[
            middlewares.auth.auth(conf['auth']),
        ],
        router=router.VersionRouter({'1.0': v1}))
    app.on_startup.append(middlewares.auth.setup)

    # Attach settings to the application instance in order to make them
    # accessible at any point of execution (e.g. request handling).
    app['conf'] = conf
    app.on_startup.append(database.setup)

    # We need to respond with Vary header time to time in order to avoid
    # issues with cache on client side.
    app.on_response_prepare.append(_inject_vary_header)

    return app
