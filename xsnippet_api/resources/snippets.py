"""
    xsnippet_api.resources.snippets
    -------------------------------

    The module implements snippets resource that provides CRUD interface
    for code snippets.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

from .resource import Resource


class Snippets(Resource):

    async def get(self):
        snippets = await self.db.snippets.find().to_list(length=20)
        return self.make_response(snippets)

    async def post(self):
        snippet = await self.read_request()

        snippet_id = await self.db.snippets.insert(snippet)
        snippet['_id'] = snippet_id

        return self.make_response(snippet, status=201)
