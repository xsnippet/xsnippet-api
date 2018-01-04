"""
    xsnippet.api.resources.syntaxes
    -------------------------------

    The module implements the resource, that allows to retrieve
    the list of supported snippet syntaxes.

    :copyright: (c) 2017 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

from .. import resource


class Syntaxes(resource.Resource):

    async def get(self):
        conf = self.request.app['conf']
        syntaxes = conf.getlist('snippet', 'syntaxes', fallback=None) or []

        return self.make_response(syntaxes, status=200)
