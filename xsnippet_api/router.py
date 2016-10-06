"""
    xsnippet_api.router
    -------------------

    Provides an aiohttp router class for API versioning. In its depth
    it's nothing more but a proxy to a certain router based on some
    input criteria.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import pkg_resources

from aiohttp import abc, web


def _get_latest_version(versions, stable=True):
    """Search ``versions`` array and return the latest one.

    The function requires a contract that an input array indeed contains at
    least one stable version in case of ``stable=True`` or at least one
    version otherwise. Examples::

       >>> get_latest_version(['1.0', '2.0', '2.1-alpha'])
       '2.0'

       >>> get_latest_version(['1.0', '2.0', '2.1-alpha'], stable=False)
       '2.1-alpha'

    :param versions: an array of string-based versions
    :param stable: search only among stable versions if ``True``
    :return: the latest version as string
    """
    # Unfortunately, `packaging.version.parse` looses original version
    # representation in favor of PEP-440. Despite the fact I doubt
    # anyone would use complex API versions (with alpha/beta notation),
    # it still better to implement things correctly and return original
    # representation. That's why we save version pairs here.
    versions = ((v, pkg_resources.parse_version(v)) for v in versions)

    # Both PEP-440 and SemVer define so called "pre-release" version such
    # as alpha or beta. Most of the time, we aren't interested in them
    # since they shouldn't be considered as stable, and hence as default
    # one. So we need to filter them out from list and don't take into
    # account in sorting below.
    if stable:
        versions = filter(lambda item: not item[1].is_prerelease, versions)

    # Sort using PEP's rules and return an original version value.
    versions = sorted(versions, key=lambda item: item[1])
    return versions[-1][0]


class VersionRouter(abc.AbstractRouter):
    """A proxy router to forward requests based on passed API version.

    Despite there are various approaches to pass API version, this router
    implements the one with a separate HTTP header. In other words it tries
    to read ``Api-Version`` header and use its value as API version to
    forward request further.

    If nothing is passed, the latest stable version is used. If wrong version
    is passed, ``412 Precondition Failed`` response is returned.

    :param routers: a 'API version' -> 'router' map
    """

    def __init__(self, routers):
        self._routers = routers
        self._latest = _get_latest_version(self._routers.keys())

    async def resolve(self, request):
        version = request.headers.get('Api-Version')

        if version is None:
            version = self._latest

        if version not in self._routers:
            raise web.HTTPPreconditionFailed()

        return await self._routers[version].resolve(request)
