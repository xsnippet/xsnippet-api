"""
    xsnippet_api.resources.snippets
    -------------------------------

    The module implements snippets resource that provides CRUD interface
    for code snippets.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import aiohttp.web as web

from .resource import Resource
from .. import services


class Snippet(Resource):

    async def get(self):
        try:
            _id = int(self.request.match_info['id'])
        except (ValueError, TypeError):
            raise web.HTTPBadRequest()

        snippet = await services.Snippet(self.db).get_one(_id)
        return self.make_response(snippet)

    async def delete(self):
        try:
            _id = int(self.request.match_info['id'])
        except (ValueError, TypeError):
            raise web.HTTPBadRequest()

        # TODO: only allow authorized users to delete their snippets

        await services.Snippet(self.db).delete(_id)
        return self.make_response('', status=204)  # No Content


class Snippets(Resource):

    async def get(self):
        snippets = await services.Snippet(self.db).get(limit=20)
        return self.make_response(snippets, status=200)

    async def post(self):
        snippet = await self.read_request()
        snippet = await services.Snippet(self.db).create(snippet)
        return self.make_response(snippet, status=201)
