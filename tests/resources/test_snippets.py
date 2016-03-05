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

    def setup(self):
        conf = get_conf(
            pkg_resources.resource_filename('xsnippet_api', 'default.conf')
        )

        self.app = create_app(conf)

    async def teardown(self):
        await self.app['db'].snippets.remove()

    async def test_get_no_snippets(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get('/snippets')

            assert resp.status == 200
            assert await resp.json() == []

    async def test_get_snippets(self):
        await self.app['db'].snippets.insert(self.snippets)

        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get('/snippets')

            assert resp.status == 200
            assert await resp.json() == self.snippets

    async def test_post_snippet(self):
        async with AIOTestApp(self.app) as testapp:
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
            snippet_db = await self.app['db'].snippets.find_one(
                {'_id': snippet_resp['_id']}
            )

            assert snippet_resp == snippet_db

    async def test_data_model_indexes_exist(self):
        res = await self.app['db'].snippets.index_information()

        assert res['author_idx']['key'] == [('author_id', 1)]
        assert res['tags_idx']['key'] == [('tags', 1)]
        assert res['updated_idx']['key'] == [('updated_at', -1)]
        assert res['created_idx']['key'] == [('created_at', -1)]

    async def test_get_snippet(self):
        async with AIOTestApp(self.app) as testapp:
            snippet = copy.deepcopy(self.snippets[0])
            del snippet['_id']

            resp = await testapp.post(
                '/snippets',
                data=json.dumps(snippet),
                headers={
                    'Content-Type': 'application/json',
                }
            )
            created = await resp.json()

            resp = await testapp.get(
                '/snippets/' + str(created['_id']),
                headers={
                    'Accept': 'application/json',
                }
            )
            assert resp.status == 200
            assert (resp.headers['Content-Type'] ==
                    'application/json; charset=utf-8')

            retrieved = await resp.json()
            assert retrieved == created

    async def test_get_snippet_not_found(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get(
                '/snippets/0123456789',
                headers={
                    'Accept': 'application/json',
                }
            )
            text = await resp.text()

            assert resp.status == 404
            assert 'Not Found' in text

    async def test_get_snippet_bad_request(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get(
                '/snippets/deadbeef',
                headers={
                    'Accept': 'application/json',
                }
            )
            text = await resp.text()

            assert resp.status == 400
            assert 'Bad Request' in text
