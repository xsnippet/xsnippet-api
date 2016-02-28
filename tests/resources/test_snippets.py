"""
    tests.resources.test_snippets
    -----------------------------

    Tests Snippets resource.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import copy
import json
import pkg_resources

from xsnippet_api.application import create_app
from xsnippet_api.conf import get_conf
from tests import AIOTestMeta, AIOTestApp


class TestSnippets(metaclass=AIOTestMeta):

    conf = get_conf(
        pkg_resources.resource_filename('xsnippet_api', 'default.conf'))

    snippets = [
        {
            '_id': 1,
            'title': 'snippet #1',
            'changeset': {
                'content': 'def foo(): pass',
            },
            'syntax': 'python',
            'tags': ['tag_a', 'tag_b'],
        },
        {
            '_id': 2,
            'title': 'snippet #2',
            'changeset': {
                'content': 'int do_something() {}',
            },
            'syntax': 'cpp',
            'tags': ['tag_c'],
        },
    ]

    async def test_get_no_snippets(self):
        app = create_app(self.conf)

        await app['db'].snippets.remove()

        async with AIOTestApp(app) as testapp:
            resp = await testapp.get('/snippets')

            assert resp.status == 200
            assert await resp.json() == []

    async def test_get_snippets(self):
        app = create_app(self.conf)

        await app['db'].snippets.remove()
        await app['db'].snippets.insert(self.snippets)

        async with AIOTestApp(app) as testapp:
            resp = await testapp.get('/snippets')

            assert resp.status == 200
            assert await resp.json() == self.snippets

    async def test_post_snippet(self):
        app = create_app(self.conf)

        await app['db'].snippets.remove()

        async with AIOTestApp(app) as testapp:
            snippet = copy.deepcopy(self.snippets[0])
            del snippet['_id']

            resp = await testapp.post(
                '/snippets',
                data=json.dumps(snippet),
                headers={
                    'Content-Type': 'application/json',
                }
            )
            assert resp.status == 201

            # ensure that posted snippet is in database
            snippet_resp = await resp.json()
            snippet_db = await app['db'].snippets.find_one(
                {'_id': snippet_resp['_id']}
            )

            assert snippet_resp == snippet_db

    async def test_data_model_indexes_exist(self):
        app = create_app(self.conf)

        res = await app['db'].snippets.index_information()

        assert res['author_idx']['key'] == [('author_id', 1)]
        assert res['tags_idx']['key'] == [('tags', 1)]
        assert res['updated_idx']['key'] == [('updated_at', -1)]
        assert res['created_idx']['key'] == [('created_at', -1)]
