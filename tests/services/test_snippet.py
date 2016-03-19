"""
    tests.services.test_snippet
    ---------------------------

    Tests Snippet service.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import datetime
import pkg_resources
import operator

import pytest
import aiohttp.web as web

from xsnippet_api.database import create_connection
from xsnippet_api.conf import get_conf
from xsnippet_api.services import Snippet

from tests import AIOTestMeta


class TestSnippet(metaclass=AIOTestMeta):

    async def setup(self):
        conf = get_conf(
            pkg_resources.resource_filename('xsnippet_api', 'default.conf'))
        self.db = create_connection(conf)
        self.service = Snippet(self.db)

        now = datetime.datetime.utcnow().replace(microsecond=0)
        self.snippets = [
            {
                'id': 1,
                'title': 'snippet #1',
                'content': 'def foo(): pass',
                'syntax': 'python',
                'tags': ['tag_a', 'tag_b'],
                'author_id': None,
                'is_public': True,
                'created_at': now,
                'updated_at': now,
            },
            {
                'id': 2,
                'title': 'snippet #2',
                'content': 'int do_something() {}',
                'syntax': 'cpp',
                'tags': ['tag_c'],
                'author_id': None,
                'is_public': True,
                'created_at': now + datetime.timedelta(100),
                'updated_at': now + datetime.timedelta(100),
            },
        ]

        await self.db.snippets.insert(self.snippets)
        # make sure all new documents won't collide with our fixture above
        await self.db['_autoincrement_ids'].find_and_modify(
            query={'_id': 'snippets'},
            update={'$set': {'next': 2}},
            upsert=True
        )

    async def teardown(self):
        await self.db.snippets.remove()

    async def test_get_one(self):
        snippet = await self.service.get_one(self.snippets[0]['id'])
        assert snippet == self.snippets[0]

    async def test_get_one_not_found(self):
        with pytest.raises(web.HTTPNotFound):
            await self.service.get_one('whatever')

    async def test_get(self):
        returned_snippets = await self.service.get()

        # Service layer returns snippets sorted in DESC order, so the
        # order is different. However, we don't care about order, we
        # are more interested in items.
        a = sorted(returned_snippets, key=operator.itemgetter('id'))
        b = sorted(self.snippets, key=operator.itemgetter('id'))

        assert a == b

    async def test_get_limit(self):
        returned_snippets = await self.service.get(limit=1)

        # the last inserted snippet should be returned by service layer,
        # so prepare it for assertion
        snippet = self.snippets[-1]

        assert len(returned_snippets) == 1
        assert returned_snippets == [snippet]

    async def test_create(self):
        snippet = {
            'title': 'my snippet',
            'content': '...',
            'syntax': 'python',
        }

        created = await self.service.create(snippet)
        created_db = await self.db.snippets.find_one(
            {'_id': created.pop('id')}
        )

        created.pop('created_at')
        created.pop('updated_at')

        created_db.pop('id')
        created_db.pop('created_at')
        created_db.pop('updated_at')

        assert created == {
            'title': 'my snippet',
            'content': '...',
            'syntax': 'python',
            'is_public': True,
            'tags': [],
            'author_id': None,
        }

        assert created == created_db

    async def test_delete(self):
        _id = self.snippets[0]['id']

        before = await self.db.snippets.find({}).to_list(None)
        assert len(before) == 2

        rv = await self.service.delete(_id)
        assert rv is None

        after = await self.db.snippets.find({}).to_list(None)
        assert len(after) == 1

    async def test_delete_not_found(self):
        with pytest.raises(web.HTTPNotFound):
            await self.service.delete(123456789)
