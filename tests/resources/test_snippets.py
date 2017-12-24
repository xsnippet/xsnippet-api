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


@pytest.fixture(scope='function')
def snippets():
    now = datetime.datetime.utcnow().replace(microsecond=0)
    return [
        {
            'id': 1,
            'title': 'snippet #1',
            'content': 'def foo(): pass',
            'syntax': 'python',
            'tags': ['tag_a', 'tag_b'],
            'created_at': now - datetime.timedelta(100),
            'updated_at': now - datetime.timedelta(100),
        },
        {
            'id': 2,
            'title': 'snippet #2',
            'content': 'int do_something() {}',
            'syntax': 'cpp',
            'tags': ['tag_c'],
            'created_at': now,
            'updated_at': now,
        },
    ]


@pytest.fixture(scope='function')
def appinstance():
    conf = get_conf(
        pkg_resources.resource_filename('xsnippet.api', 'default.conf'))
    conf['auth'] = {'secret': 'SWORDFISH'}
    return create_app(conf)


@pytest.fixture(scope='function')
async def db(testapp, appinstance):
    # It's important to depend on testapp, as it starts the app and we create
    # DB connection during startup.
    return appinstance['db']


@pytest.fixture(scope='function')
async def testapp(request, loop, appinstance, test_client):
    request.addfinalizer(
        lambda: loop.run_until_complete(appinstance['db'].snippets.remove()))
    return await test_client(appinstance)


def _compare_snippets(snippet_db, snippet_api):
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


async def test_get_no_snippets(testapp):
    resp = await testapp.get(
        '/snippets',
        headers={
            'Accept': 'application/json',
        })

    assert resp.status == 200
    assert await resp.json() == []


async def test_get_snippets(testapp, snippets, db):
    await db.snippets.insert(snippets)

    resp = await testapp.get(
        '/snippets',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 200

    # snippets must be returned in descending order (newer first)
    expected = sorted(
        snippets,
        key=operator.itemgetter('created_at'),
        reverse=True)

    for snippet_db, snippet_api in zip(expected, await resp.json()):
        _compare_snippets(snippet_db, snippet_api)


async def test_get_snippets_filter_by_title(testapp, snippets, db):
    await db.snippets.insert(snippets)

    resp = await testapp.get(
        '/snippets?title=snippet+%231',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 200
    expected = [snippets[0]]
    for snippet_db, snippet_api in zip(expected, await resp.json()):
        _compare_snippets(snippet_db, snippet_api)

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


async def test_get_snippets_filter_by_title_bad_request(testapp, snippets, db):
    await db.snippets.insert(snippets)

    resp = await testapp.get(
        '/snippets?title=',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 400
    assert await resp.json() == {
        'message': '`title` - empty values not allowed.'
    }


async def test_get_snippets_filter_by_tag(testapp, snippets, db):
    await db.snippets.insert(snippets)

    resp = await testapp.get(
        '/snippets?tag=tag_c',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 200
    expected = [snippets[1]]
    for snippet_db, snippet_api in zip(expected, await resp.json()):
        _compare_snippets(snippet_db, snippet_api)

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
async def test_get_snippets_filter_by_tag_bad_request(
        value, testapp, snippets, db):
    await db.snippets.insert(snippets)

    resp = await testapp.get(
        '/snippets?tag=' + value,
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 400
    assert await resp.json() == {
        'message': "`tag` - value does not match regex '[\\w_-]+'."
    }


async def test_get_snippets_filter_by_title_and_tag(testapp, snippets, db):
    await db.snippets.insert(snippets)

    resp = await testapp.get(
        '/snippets?title=snippet+%231&tag=tag_a',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 200
    expected = [snippets[0]]
    for snippet_db, snippet_api in zip(expected, await resp.json()):
        _compare_snippets(snippet_db, snippet_api)

    nonexistent = await testapp.get(
        '/snippets?title=snippet+%231&tag=tag_c',
        headers={
            'Accept': 'application/json',
        })
    assert nonexistent.status == 200
    assert list(nonexistent.json()) == []


async def test_get_snippets_filter_by_title_and_tag_with_pagination(
        testapp, snippets, db):
    now = datetime.datetime.utcnow().replace(microsecond=0)
    snippet = {
        'id': 3,
        'title': 'snippet #1',
        'content': '(println "Hello, World!")',
        'syntax': 'clojure',
        'tags': ['tag_a'],
        'created_at': now,
        'updated_at': now,
    }

    await db.snippets.insert(snippets + [snippet])

    resp = await testapp.get(
        '/snippets?title=snippet+%231&tag=tag_a&limit=1',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 200
    expected = [snippet]
    for snippet_db, snippet_api in zip(expected, await resp.json()):
        _compare_snippets(snippet_db, snippet_api)

    resp = await testapp.get(
        '/snippets?title=snippet+%231&tag=tag_a&limit=1&marker=3',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 200
    expected = [snippets[0]]
    for snippet_db, snippet_api in zip(expected, await resp.json()):
        _compare_snippets(snippet_db, snippet_api)


async def test_get_snippets_pagination(testapp, snippets, db):
    now = datetime.datetime.utcnow().replace(microsecond=0)
    snippet = {
        'id': 3,
        'title': 'snippet #3',
        'content': '(println "Hello, World!")',
        'syntax': 'clojure',
        'tags': ['tag_b'],
        'created_at': now,
        'updated_at': now,
    }

    await db.snippets.insert(snippets + [snippet])

    # ask for one latest snippet
    resp = await testapp.get(
        '/snippets?limit=1',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 200

    snippet_api = await resp.json()
    assert len(snippet_api) == 1
    _compare_snippets(snippet, snippet_api[0])

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
        snippets,
        key=operator.itemgetter('created_at'),
        reverse=True)

    for snippet_db, snippet_api in zip(expected, await resp.json()):
        _compare_snippets(snippet_db, snippet_api)


async def test_get_snippets_pagination_not_found(testapp):
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


async def test_get_snippets_pagination_bad_request_limit(testapp):
    resp = await testapp.get(
        '/snippets?limit=deadbeef',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 400
    assert await resp.json() == {
        'message': '`limit` - must be of integer type.',
    }


async def test_get_snippets_pagination_bad_request_limit_negative(testapp):
    resp = await testapp.get(
        '/snippets?limit=-1',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 400
    assert await resp.json() == {
        'message': '`limit` - min value is 1.',
    }


async def test_get_snippets_pagination_bad_request_marker(testapp):
    resp = await testapp.get(
        '/snippets?marker=deadbeef',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 400
    assert await resp.json() == {
        'message': '`marker` - must be of integer type.',
    }


async def test_get_snippets_pagination_bad_request_unknown_param(testapp):
    resp = await testapp.get(
        '/snippets?deadbeef=1',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 400
    assert await resp.json() == {
        'message': '`deadbeef` - unknown field.',
    }


async def test_post_snippet(testapp, snippets, db):
    snippet = snippets[0]
    for key in ('id', 'created_at', 'updated_at'):
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
    snippet_db = await db.snippets.find_one(
        {'_id': snippet_resp['id']}
    )

    _compare_snippets(snippet_db, snippet_resp)


@pytest.mark.parametrize('name, value', [
    ('title', 42),                          # must be string
    ('content', 42),                        # must be string
    ('tags', ['a tag with whitespaces']),   # tag must not contain spaces
    ('created_at', '2016-09-11T19:07:43'),  # readonly
    ('updated_at', '2016-09-11T19:07:43'),  # readonly
    ('non-existent-key', 'must not be accepted'),
])
async def test_post_snippet_malformed_snippet(name, value, testapp, snippets):
    snippet = snippets[0]
    for key in ('id', 'created_at', 'updated_at'):
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


async def test_post_snippet_syntax_enum_allowed(
        testapp, snippets, db, appinstance):
    appinstance['conf']['snippet']['syntaxes'] = 'python\nclojure'

    snippet = snippets[0]
    for key in ('id', 'created_at', 'updated_at'):
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
    snippet_db = await db.snippets.find_one(
        {'_id': snippet_resp['id']}
    )

    _compare_snippets(snippet_db, snippet_resp)


async def test_post_snippet_syntax_enum_not_allowed(
        testapp, snippets, appinstance):
    appinstance['conf']['snippet']['syntaxes'] = 'python\nclojure'

    snippet = snippets[0]
    for key in ('id', 'created_at', 'updated_at'):
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


async def test_data_model_indexes_exist(db):
    res = await db.snippets.index_information()

    assert res['title_idx']['key'] == [('title', 1)]
    assert res['title_idx']['partialFilterExpression'] == {
        'title': {'$type': 'string'}
    }
    assert res['tags_idx']['key'] == [('tags', 1)]
    assert res['updated_idx']['key'] == [('updated_at', -1)]
    assert res['created_idx']['key'] == [('created_at', -1)]


async def test_get_snippet(testapp, snippets, db):
    awaited = copy.deepcopy(snippets[0])
    await db.snippets.insert(snippets)

    resp = await testapp.get(
        '/snippets/' + str(awaited['id']),
        headers={
            'Accept': 'application/json',
        })

    assert resp.status == 200
    assert (resp.headers['Content-Type'] ==
            'application/json; charset=utf-8')

    _compare_snippets(awaited, await resp.json())


async def test_get_snippet_not_found(testapp):
    resp = await testapp.get(
        '/snippets/0123456789',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 404
    assert await resp.json() == {
        'message': 'Sorry, cannot find the requested snippet.',
    }


async def test_get_snippet_bad_request(testapp):
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


async def test_delete_snippet(testapp, snippets, db):
    created = snippets[0]
    await db.snippets.insert(created)

    resp = await testapp.delete(
        '/snippets/' + str(created['id']),
        headers={
            'Accept': 'application/json',
        })

    assert resp.status == 204


async def test_delete_snippet_not_found(testapp):
    resp = await testapp.delete(
        '/snippets/' + str(123456789),
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 404
    assert await resp.json() == {
        'message': 'Sorry, cannot find the requested snippet.',
    }


async def test_delete_snippet_bad_request(testapp):
    resp = await testapp.delete(
        '/snippets/deadbeef',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 400
    assert await resp.json() == {
        'message': '`id` - must be of integer type.'
    }
