"""
    tests.resources.test_snippets
    -----------------------------

    Tests Snippets resource.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import re
import copy
import json
import datetime
import operator

import pkg_resources
import pytest

from xsnippet.api.application import create_app
from xsnippet.api.conf import get_conf
from tests import AIOTestMeta, AIOTestApp


class TestSnippets(metaclass=AIOTestMeta):

    def setup(self):
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
                'created_at': now - datetime.timedelta(100),
                'updated_at': now - datetime.timedelta(100),
            },
            {
                'id': 2,
                'title': 'snippet #2',
                'content': 'int do_something() {}',
                'syntax': 'cpp',
                'tags': ['tag_c'],
                'author_id': None,
                'is_public': True,
                'created_at': now,
                'updated_at': now,
            },
        ]

        conf = get_conf(
            pkg_resources.resource_filename('xsnippet.api', 'default.conf'))
        conf['auth'] = {'secret': 'SWORDFISH'}
        self.app = create_app(conf)

    async def teardown(self):
        await self.app['db'].snippets.remove()

    def _compare_snippets(self, snippet_db, snippet_api):
        # compare datetimes
        assert (
            snippet_api.pop('created_at') ==
            snippet_db.pop('created_at').isoformat()
        )
        assert (
            snippet_api.pop('updated_at') ==
            snippet_db.pop('updated_at').isoformat()
        )

        # compare rest of snippet
        assert snippet_api == snippet_db

    async def test_get_no_snippets(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get(
                '/snippets',
                headers={
                    'Accept': 'application/json',
                })

            assert resp.status == 200
            assert await resp.json() == []

    async def test_get_snippets(self):
        async with AIOTestApp(self.app) as testapp:
            await self.app['db'].snippets.insert(self.snippets)

            resp = await testapp.get(
                '/snippets',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 200

            # snippets must be returned in descending order (newer first)
            expected = sorted(
                self.snippets,
                key=operator.itemgetter('created_at'),
                reverse=True)

            for snippet_db, snippet_api in zip(expected, await resp.json()):
                self._compare_snippets(snippet_db, snippet_api)

    async def test_get_snippets_filter_by_title(self):
        async with AIOTestApp(self.app) as testapp:
            await self.app['db'].snippets.insert(self.snippets)

            resp = await testapp.get(
                '/snippets?title=snippet+%231',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 200
            expected = [self.snippets[0]]
            for snippet_db, snippet_api in zip(expected, await resp.json()):
                self._compare_snippets(snippet_db, snippet_api)

            nonexistent = await testapp.get(
                '/snippets?title=nonexistent',
                headers={
                    'Accept': 'application/json',
                })
            assert nonexistent.status == 200
            assert list(nonexistent.json()) == []

            regexes_are_escaped = await testapp.get(
                '/snippets?title=%5Esnippet.%2A',  # title=^snippet.*
                headers={
                    'Accept': 'application/json',
                })
            assert regexes_are_escaped.status == 200
            assert list(regexes_are_escaped.json()) == []

    async def test_get_snippets_filter_by_title_bad_request(self):
        async with AIOTestApp(self.app) as testapp:
            await self.app['db'].snippets.insert(self.snippets)

            resp = await testapp.get(
                '/snippets?title=',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 400
            assert await resp.json() == {
                'message': '`title` - empty values not allowed.'
            }

    async def test_get_snippets_filter_by_tag(self):
        async with AIOTestApp(self.app) as testapp:
            await self.app['db'].snippets.insert(self.snippets)

            resp = await testapp.get(
                '/snippets?tag=tag_c',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 200
            expected = [self.snippets[1]]
            for snippet_db, snippet_api in zip(expected, await resp.json()):
                self._compare_snippets(snippet_db, snippet_api)

            nonexistent = await testapp.get(
                '/snippets?tag=nonexistent_tag',
                headers={
                    'Accept': 'application/json',
                })
            assert nonexistent.status == 200
            assert list(nonexistent.json()) == []

    @pytest.mark.parametrize(
        'value',
        ['', 'test%20tag'],
        ids=['empty', 'whitespace']
    )
    async def test_get_snippets_filter_by_tag_bad_request(self, value):
        async with AIOTestApp(self.app) as testapp:
            await self.app['db'].snippets.insert(self.snippets)

            resp = await testapp.get(
                '/snippets?tag=' + value,
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 400
            assert await resp.json() == {
                'message': "`tag` - value does not match regex '[\\w_-]+'."
            }

    async def test_get_snippets_filter_by_title_and_tag(self):
        async with AIOTestApp(self.app) as testapp:
            await self.app['db'].snippets.insert(self.snippets)

            resp = await testapp.get(
                '/snippets?title=snippet+%231&tag=tag_a',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 200
            expected = [self.snippets[0]]
            for snippet_db, snippet_api in zip(expected, await resp.json()):
                self._compare_snippets(snippet_db, snippet_api)

            nonexistent = await testapp.get(
                '/snippets?title=snippet+%231&tag=tag_c',
                headers={
                    'Accept': 'application/json',
                })
            assert nonexistent.status == 200
            assert list(nonexistent.json()) == []

    async def test_get_snippets_filter_by_title_and_tag_with_pagination(self):
        now = datetime.datetime.utcnow().replace(microsecond=0)
        snippet = {
            'id': 3,
            'title': 'snippet #1',
            'content': '(println "Hello, World!")',
            'syntax': 'clojure',
            'tags': ['tag_a'],
            'author_id': None,
            'is_public': True,
            'created_at': now,
            'updated_at': now,
        }

        async with AIOTestApp(self.app) as testapp:
            await self.app['db'].snippets.insert(self.snippets + [snippet])

            resp = await testapp.get(
                '/snippets?title=snippet+%231&tag=tag_a&limit=1',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 200
            expected = [snippet]
            for snippet_db, snippet_api in zip(expected, await resp.json()):
                self._compare_snippets(snippet_db, snippet_api)

            resp = await testapp.get(
                '/snippets?title=snippet+%231&tag=tag_a&limit=1&marker=3',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 200
            expected = [self.snippets[0]]
            for snippet_db, snippet_api in zip(expected, await resp.json()):
                self._compare_snippets(snippet_db, snippet_api)

    async def test_get_snippets_pagination(self):
        now = datetime.datetime.utcnow().replace(microsecond=0)
        snippet = {
            'id': 3,
            'title': 'snippet #3',
            'content': '(println "Hello, World!")',
            'syntax': 'clojure',
            'tags': ['tag_b'],
            'author_id': None,
            'is_public': True,
            'created_at': now,
            'updated_at': now,
        }

        async with AIOTestApp(self.app) as testapp:
            await self.app['db'].snippets.insert(self.snippets + [snippet])

            # ask for one latest snippet
            resp = await testapp.get(
                '/snippets?limit=1',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 200

            snippet_api = await resp.json()
            assert len(snippet_api) == 1
            self._compare_snippets(snippet, snippet_api[0])

            # ask for (up to) 10 snippets created before the last seen one
            marker = snippet_api[0]['id']
            resp = await testapp.get(
                '/snippets?limit=10&marker=%d' % marker,
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 200

            # snippets must be returned in descending order (newer first)
            expected = sorted(
                self.snippets,
                key=operator.itemgetter('created_at'),
                reverse=True)

            for snippet_db, snippet_api in zip(expected, await resp.json()):
                self._compare_snippets(snippet_db, snippet_api)

    async def test_get_snippets_pagination_not_found(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get(
                '/snippets?limit=10&marker=1234567890',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 404
            assert await resp.json() == {
                'message': 'Sorry, cannot complete the request since `marker` '
                           'points to a nonexistent snippet.',
            }

    async def test_get_snippets_pagination_bad_request_limit(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get(
                '/snippets?limit=deadbeef',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 400
            assert await resp.json() == {
                'message': '`limit` - must be of integer type.',
            }

    async def test_get_snippets_pagination_bad_request_limit_negative(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get(
                '/snippets?limit=-1',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 400
            assert await resp.json() == {
                'message': '`limit` - min value is 1.',
            }

    async def test_get_snippets_pagination_bad_request_marker(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get(
                '/snippets?marker=deadbeef',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 400
            assert await resp.json() == {
                'message': '`marker` - must be of integer type.',
            }

    async def test_get_snippets_pagination_bad_request_unknown_param(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get(
                '/snippets?deadbeef=1',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 400
            assert await resp.json() == {
                'message': '`deadbeef` - unknown field.',
            }

    async def test_post_snippet(self):
        async with AIOTestApp(self.app) as testapp:
            snippet = self.snippets[0]
            for key in ('id', 'author_id', 'created_at', 'updated_at'):
                del snippet[key]

            resp = await testapp.post(
                '/snippets',
                data=json.dumps(snippet),
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                })
            assert resp.status == 201

            snippet_resp = await resp.json()
            snippet_db = await self.app['db'].snippets.find_one(
                {'_id': snippet_resp['id']}
            )

            self._compare_snippets(snippet_db, snippet_resp)

    @pytest.mark.parametrize('name, value', [
        ('title', 42),                          # must be string
        ('content', 42),                        # must be string
        ('tags', ['a tag with whitespaces']),   # tag must not contain spaces
        ('is_public', 'yes'),                   # must be bool
        ('author_id', 42),                      # readonly
        ('created_at', '2016-09-11T19:07:43'),  # readonly
        ('updated_at', '2016-09-11T19:07:43'),  # readonly
        ('non-existent-key', 'must not be accepted'),
    ])
    async def test_post_snippet_malformed_snippet(self, name, value):
        async with AIOTestApp(self.app) as testapp:
            snippet = self.snippets[0]
            for key in ('id', 'author_id', 'created_at', 'updated_at'):
                del snippet[key]
            snippet[name] = value

            resp = await testapp.post(
                '/snippets',
                data=json.dumps(snippet),
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                })
            assert resp.status == 400

            error_resp = await resp.json()
            assert re.match(
                'Cannot create a new snippet, passed data are incorrect. '
                'Found issues: `%s` - .*' % name,
                error_resp['message'])

    async def test_post_snippet_syntax_enum_allowed(self):
        async with AIOTestApp(self.app) as testapp:
            self.app['conf']['snippet']['syntaxes'] = 'python\nclojure'

            snippet = self.snippets[0]
            for key in ('id', 'author_id', 'created_at', 'updated_at'):
                del snippet[key]

            snippet['syntax'] = 'python'

            resp = await testapp.post(
                '/snippets',
                data=json.dumps(snippet),
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                })
            assert resp.status == 201

            snippet_resp = await resp.json()
            snippet_db = await self.app['db'].snippets.find_one(
                {'_id': snippet_resp['id']}
            )

            self._compare_snippets(snippet_db, snippet_resp)

    async def test_post_snippet_syntax_enum_not_allowed(self):
        async with AIOTestApp(self.app) as testapp:
            self.app['conf']['snippet']['syntaxes'] = 'python\nclojure'

            snippet = self.snippets[0]
            for key in ('id', 'author_id', 'created_at', 'updated_at'):
                del snippet[key]

            snippet['syntax'] = 'go'

            resp = await testapp.post(
                '/snippets',
                data=json.dumps(snippet),
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                })
            assert resp.status == 400

            error_resp = await resp.json()
            assert re.match(
                'Cannot create a new snippet, passed data are incorrect. '
                'Found issues: `syntax` - invalid value.',
                error_resp['message'])

    async def test_data_model_indexes_exist(self):
        async with AIOTestApp(self.app):
            res = await self.app['db'].snippets.index_information()

            assert res['author_idx']['key'] == [('author_id', 1)]
            assert res['title_idx']['key'] == [('title', 1)]
            assert res['title_idx']['partialFilterExpression'] == {
                'title': {'$type': 'string'}
            }
            assert res['tags_idx']['key'] == [('tags', 1)]
            assert res['updated_idx']['key'] == [('updated_at', -1)]
            assert res['created_idx']['key'] == [('created_at', -1)]

    async def test_get_snippet(self):
        awaited = copy.deepcopy(self.snippets[0])

        async with AIOTestApp(self.app) as testapp:
            await self.app['db'].snippets.insert(self.snippets)

            resp = await testapp.get(
                '/snippets/' + str(awaited['id']),
                headers={
                    'Accept': 'application/json',
                })

            assert resp.status == 200
            assert (resp.headers['Content-Type'] ==
                    'application/json; charset=utf-8')

            self._compare_snippets(awaited, await resp.json())

    async def test_get_snippet_not_found(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get(
                '/snippets/0123456789',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 404
            assert await resp.json() == {
                'message': 'Sorry, cannot find the requested snippet.',
            }

    async def test_get_snippet_bad_request(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get(
                '/snippets/deadbeef',
                headers={
                    'Accept': 'application/json',
                }
            )
            assert resp.status == 400
            assert await resp.json() == {
                'message': '`id` - must be of integer type.'
            }

    async def test_delete_snippet(self):
        created = self.snippets[0]
        async with AIOTestApp(self.app) as testapp:
            await self.app['db'].snippets.insert(created)

            resp = await testapp.delete(
                '/snippets/' + str(created['id']),
                headers={
                    'Accept': 'application/json',
                })

            assert resp.status == 204

    async def test_delete_snippet_not_found(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.delete(
                '/snippets/' + str(123456789),
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 404
            assert await resp.json() == {
                'message': 'Sorry, cannot find the requested snippet.',
            }

    async def test_delete_snippet_bad_request(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.delete(
                '/snippets/deadbeef',
                headers={
                    'Accept': 'application/json',
                })
            assert resp.status == 400
            assert await resp.json() == {
                'message': '`id` - must be of integer type.'
            }
