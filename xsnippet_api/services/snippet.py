"""
    xsnippet_api.services.snippet
    -----------------------------

    Snippet service implements domain business logic for managing
    snippets. Its purpose is to avoid writing business logic in
    RESTful API.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import datetime

import aiohttp.web as web
import pymongo


class Snippet:

    def __init__(self, db):
        self.db = db

    async def create(self, snippet):
        snippet = self._normalize(snippet)
        snippet_id = await self.db.snippets.insert(snippet)
        snippet['id'] = snippet_id
        return snippet

    async def get(self, *, limit=100):
        snippets = await self.db.snippets.find()\
            .sort('created_at', pymongo.DESCENDING)\
            .limit(limit)\
            .to_list(None)

        return snippets

    async def get_one(self, id):
        snippet = await self.db.snippets.find_one({'_id': id})

        if snippet is None:
            # TODO: raise business domain exception instead
            raise web.HTTPNotFound()

        return snippet

    def _normalize(self, snippet):
        rv = dict({
            'title': None,
            'author_id': None,
            'syntax': 'text',
            'is_public': True,
            'tags': [],
        }, **snippet)

        rv['created_at'] = datetime.datetime.utcnow().replace(microsecond=0)
        rv['updated_at'] = rv['created_at']

        return rv
