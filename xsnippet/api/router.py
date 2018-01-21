"""
    xsnippet.api.router
    -------------------

    Provides an aiohttp router class for API versioning. In its depth
    it's nothing more but a proxy to a certain router based on some
    input criteria.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

from aiohttp import abc, web, web_urldispatcher


class VersionRouter(abc.AbstractRouter):
    """A proxy router to forward requests based on passed API version.

    Despite there are various approaches to pass API version, this router
    implements the one with a separate HTTP header. In other words it tries
    to read ``Api-Version`` header and use its value as API version to
    forward request further.

    If nothing is passed, the latest stable version is used. If wrong version
    is passed, ``412 Precondition Failed`` response is returned.

    :param routers: a 'API version' -> 'router' map
    :param default: an API version to be used if 'Api-Version' was omitted
    """

    def __init__(self, routers, *, default):
        self._routers = routers
        self._default = default

    async def resolve(self, request):
        version = request.headers.get('Api-Version')

        if version is None:
            version = self._default

        if version not in self._routers:
            return web_urldispatcher.MatchInfoError(web.HTTPNotAcceptable())

        return await self._routers[version].resolve(request)
