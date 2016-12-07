"""
    xsnippet_api.application
    ------------------------

    Provides a factory function to create an application instance,
    ready to be served by :function:`aiohttp.web.run_app`.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import collections
import functools

import pkg_resources
from aiohttp import web, web_urldispatcher

from . import database, router, middlewares


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
    # We need to import all the resources in order to evaluate @endpoint
    # decorator, so they can be collected and passed to VersionRouter.
    from . import resources  # noqa
    app = web.Application(
        middlewares=[
            functools.partial(middlewares.auth, conf['auth']),
        ])

    # Since aiohttp 1.1, UrlDispatcher has one mandatory attribute -
    # application instance, that's used internally only in subapps
    # feature. Unfortunately, there's no legal way to pass application
    # when router is created or vice versa. Either way we need to
    # access internal variable in order to do so.
    #
    # See https://github.com/KeepSafe/aiohttp/issues/1373 for details.
    app._router = router.VersionRouter(endpoint.collect(app))

    # Attach settings to the application instance in order to make them
    # accessible at any point of execution (e.g. request handling).
    app['conf'] = conf
    app['db'] = database.create_connection(conf)

    # We need to respond with Vary header time to time in order to avoid
    # issues with cache on client side.
    app.on_response_prepare.append(_inject_vary_header)

    return app


class endpoint:
    """Define a RESTful API endpoint.

    Usage example:

        @endpoint('/myresources/{id}', '1.0')
        class MyResource(web.View):
            def get(self):
                pass

    :param route: a route to a wrapped resource
    :param version: initial supported API version
    :param end_version: last supported version; latest version if None
    """

    _Item = collections.namedtuple('ResourceItem', [
        'resource',
        'route',
        'version',
        'end_version',
    ])

    _registry = []

    def __init__(self, route, version, end_version=None):
        self._options = (route, version, end_version)

    def __call__(self, resource):
        self._registry.append(self._Item(resource, *self._options))
        return resource

    @classmethod
    def collect(cls, app):
        rv = {}

        # Create routers for each discovered API version. The main reason why
        # we need that so early is to register resources in all needed routers
        # according to supported version range.
        for item in cls._registry:
            rv[item.version] = web_urldispatcher.UrlDispatcher(app)

        for item in cls._registry:
            # If there's no end_version then a resource is still working, and
            # latest discovered version should be considered as end_version.
            end_version = item.end_version or sorted(
                rv.keys(),
                key=pkg_resources.parse_version
            )[-1]

            V = pkg_resources.parse_version

            for version in rv.keys():
                if V(item.version) <= V(version) <= V(end_version):
                    rv[version].add_route('*', item.route, item.resource)

        return rv
