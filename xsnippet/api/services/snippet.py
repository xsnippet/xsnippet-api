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
import re

import pymongo

from .. import exceptions


class Snippet:

    def __init__(self, db):
        self.db = db

    async def create(self, snippet):
        snippet = self._normalize(snippet)
        snippet_id = await self.db.snippets.insert(snippet)
        snippet['id'] = snippet_id
        return snippet

    async def get(self, *, title=None, tag=None, limit=100, marker=None):
        condition = {}

        if title is not None:
            condition['title'] = {'$regex': '^' + re.escape(title) + '.*'}
        if tag is not None:
            condition['tags'] = tag

        if marker:
            specimen = await self.db.snippets.find_one({'_id': marker})
            if not specimen:
                raise exceptions.SnippetNotFound(
                    'Sorry, cannot complete the request since `marker` '
                    'points to a nonexistent snippet.')

            condition['$and'] = [
                {'_id': {'$lt': specimen['id']}},
                {'created_at': {'$lte': specimen['created_at']}},
            ]

        query = self.db.snippets.find(condition).sort([
            ('_id', pymongo.DESCENDING),
            ('created_at', pymongo.DESCENDING)
        ])
        return await query.limit(limit).to_list(None)

    async def get_one(self, id):
        snippet = await self.db.snippets.find_one({'_id': id})

        if snippet is None:
            raise exceptions.SnippetNotFound(
                'Sorry, cannot find the requested snippet.')

        return snippet

    async def delete(self, id):
        result = await self.db.snippets.remove({'_id': id})
        if not result['n']:
            raise exceptions.SnippetNotFound(
                'Sorry, cannot find the requested snippet.')

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
