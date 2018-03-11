"""
    xsnippet.api.services.snippet
    -----------------------------

    Snippet service implements domain business logic for managing
    snippets. Its purpose is to avoid writing business logic in
    RESTful API.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import datetime
import re

import picobox
import pymongo

from .. import exceptions


class Snippet:

    _pagination = {
        'forward': {
            'filters': {
                'created_at': '$lte',
                '_id': '$lt',
            },
            'sort': {
                'created_at': pymongo.DESCENDING,
                '_id': pymongo.DESCENDING,
            }
        },
        'backward': {
            'filters': {
                'created_at': '$gte',
                '_id': '$gte',
            },
            'sort': {
                'created_at': pymongo.ASCENDING,
                '_id': pymongo.ASCENDING,
            }
        },
    }

    @picobox.pass_('database')
    def __init__(self, database):
        self.db = database

    async def create(self, snippet):
        now = datetime.datetime.utcnow().replace(microsecond=0)

        snippet = self._normalize(snippet)
        snippet['changesets'] = [
            {
                'content': snippet.pop('content'),
                'created_at': now,
            },
        ]
        snippet['created_at'] = now
        snippet['updated_at'] = now

        snippet_id = await self.db.snippets.insert(snippet)
        snippet['id'] = snippet_id
        snippet['content'] = snippet.pop('changesets', [])[0]['content']

        return snippet

    async def update(self, snippet):
        now = datetime.datetime.utcnow().replace(microsecond=0)
        snippet['updated_at'] = now

        parameters = {'$set': snippet}

        if snippet.get('content'):
            parameters['$push'] = {
                'changesets': {
                    'content': snippet.pop('content'),
                    'created_at': now,
                }
            }

        result = await self.db.snippets.update(
            {'_id': snippet['id']},
            parameters,
        )

        if not result['n']:
            raise exceptions.SnippetNotFound(
                'Sorry, cannot find the requested snippet.')

        return await self.get_one(snippet['id'])

    async def replace(self, snippet):
        return await self.update(self._normalize(snippet))

    async def get(self, *, title=None, tag=None, syntax=None, limit=100,
                  marker=None, direction='forward'):
        condition = {}

        sort = self._pagination[direction]['sort']
        filters = self._pagination[direction]['filters']

        if title is not None:
            condition['title'] = {'$regex': '^' + re.escape(title) + '.*'}
        if tag is not None:
            condition['tags'] = tag
        if syntax is not None:
            condition['syntax'] = syntax

        if marker:
            specimen = await self.db.snippets.find_one({'_id': marker})
            if not specimen:
                raise exceptions.SnippetNotFound(
                    'Sorry, cannot complete the request since `marker` '
                    'points to a nonexistent snippet.')

            condition['$and'] = [
                {'created_at': {filters['created_at']: specimen['created_at']}},
                {'_id': {filters['_id']: specimen['id']}},
            ]

        # use a compound sorting key (created_at, _id) to avoid the ambiguity
        # of equal created_at values (the only attribute of a snippet, that
        # is guaranteed to be unique is the primary key - _id). There is a
        # corresponding index on (created_at, _id), that ensures this operation
        # can be performed efficiently (mongo does not need to sort documents
        # at all - it just walks over the btree index in chosen order)
        query = self.db.snippets.find(condition).sort([
            ('created_at', sort['created_at']),
            ('_id', sort['_id']),
        ])

        snippets = await query.limit(limit).to_list(None)
        for snippet in snippets:
            snippet['content'] = snippet.pop('changesets', [])[-1]['content']
        return snippets

    async def get_one(self, id):
        snippet = await self.db.snippets.find_one({'_id': id})

        if snippet is None:
            raise exceptions.SnippetNotFound(
                'Sorry, cannot find the requested snippet.')

        snippet['content'] = snippet.pop('changesets', [])[-1]['content']
        return snippet

    async def delete(self, id):
        result = await self.db.snippets.remove({'_id': id})
        if not result['n']:
            raise exceptions.SnippetNotFound(
                'Sorry, cannot find the requested snippet.')

    def _normalize(self, snippet):
        rv = dict({
            'title': None,
            'syntax': None,
            'tags': [],
        }, **snippet)
        return rv
