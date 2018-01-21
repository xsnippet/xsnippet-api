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

import pytest


@pytest.fixture(scope='function')
async def snippets(testdatabase):
    now = datetime.datetime.utcnow().replace(microsecond=0)
    snippets = [
        {
            'id': 1,
            'title': 'snippet #1',
            'changesets': [
                {'content': 'def foo(): pass'},
            ],
            'syntax': 'python',
            'tags': ['tag_a', 'tag_b'],
            'created_at': now - datetime.timedelta(100),
            'updated_at': now - datetime.timedelta(100),
        },
        {
            'id': 2,
            'title': 'snippet #2',
            'changesets': [
                {'content': 'int do_something() {}'},
            ],
            'syntax': 'cpp',
            'tags': ['tag_c'],
            'created_at': now,
            'updated_at': now,
        },
    ]
    await testdatabase.snippets.insert(snippets)
    return snippets


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

    # compare content with the latest changeset
    assert (
        snippet_api.pop('content') ==
        snippet_db.pop('changesets')[-1]['content']
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


async def test_get_snippets(testapp, snippets):
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


async def test_get_snippets_filter_by_title(testapp, snippets):
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


async def test_get_snippets_filter_by_title_bad_request(testapp, snippets):
    resp = await testapp.get(
        '/snippets?title=',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 400
    assert await resp.json() == {
        'message': '`title` - empty values not allowed.'
    }


async def test_get_snippets_filter_by_tag(testapp, snippets):
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
async def test_get_snippets_filter_by_tag_bad_request(value, testapp, snippets):
    resp = await testapp.get(
        '/snippets?tag=' + value,
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 400
    assert await resp.json() == {
        'message': "`tag` - value does not match regex '[\\w_-]+'."
    }


async def test_get_snippets_filter_by_syntax(testapp, snippets):
    resp = await testapp.get(
        '/snippets?syntax=python',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 200
    expected = [snippets[0]]
    for snippet_db, snippet_api in zip(expected, await resp.json()):
        _compare_snippets(snippet_db, snippet_api)

    nonexistent = await testapp.get(
        '/snippets?syntax=javascript',
        headers={
            'Accept': 'application/json',
        })
    assert nonexistent.status == 200
    assert list(nonexistent.json()) == []


@pytest.mark.parametrize(
    'value',
    ['', 'ololo'],
    ids=['empty', 'non-exist']
)
async def test_get_snippets_filter_by_syntax_bad_request(value, testapp, testconf, snippets):
    testconf['snippet']['syntaxes'] = 'python\nclojure'

    resp = await testapp.get(
        '/snippets?syntax=' + value,
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 400
    assert await resp.json() == {
        'message': '`syntax` - unallowed value %s.' % value
    }


async def test_get_snippets_filter_by_title_and_tag(testapp, snippets):
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


async def test_get_snippets_filter_by_title_and_tag_with_pagination(testapp, testdatabase, snippets):  # noqa
    now = datetime.datetime.utcnow().replace(microsecond=0)
    snippet = {
        'id': 3,
        'title': 'snippet #1',
        'changesets': [
            {'content': '(println "Hello, World!")'},
        ],
        'syntax': 'clojure',
        'tags': ['tag_a'],
        'created_at': now,
        'updated_at': now,
    }
    await testdatabase.snippets.insert([snippet])

    resp = await testapp.get(
        '/snippets?title=snippet+%231&tag=tag_a&limit=1',
        headers={
            'Accept': 'application/json',
            'Host': 'api.xsnippet.org',
            'X-Forwarded-Proto': 'https',
        })
    assert resp.status == 200
    expected = [snippet]
    for snippet_db, snippet_api in zip(expected, await resp.json()):
        _compare_snippets(snippet_db, snippet_api)
    # Check that urls in Link preserve the additional query params
    expected_link1 = (
        '<https://api.xsnippet.org/snippets?title=snippet+%231&tag=tag_a&limit=1>; rel="first", '
        '<https://api.xsnippet.org/snippets?title=snippet+%231&tag=tag_a&limit=1&marker=3>; rel="next"'  # noqa
    )
    assert resp.headers['Link'] == expected_link1

    resp = await testapp.get(
        '/snippets?title=snippet+%231&tag=tag_a&limit=1&marker=3',
        headers={
            'Accept': 'application/json',
            'Host': 'api.xsnippet.org',
            'X-Forwarded-Proto': 'https',
        })
    assert resp.status == 200
    expected = [snippets[0]]
    for snippet_db, snippet_api in zip(expected, await resp.json()):
        _compare_snippets(snippet_db, snippet_api)
    # Check that urls in Link preserve the additional query params
    expected_link2 = (
        '<https://api.xsnippet.org/snippets?title=snippet+%231&tag=tag_a&limit=1>; rel="first", '
        '<https://api.xsnippet.org/snippets?title=snippet+%231&tag=tag_a&limit=1>; rel="prev"'
    )
    assert resp.headers['Link'] == expected_link2


async def test_get_snippets_pagination(testapp, testdatabase, snippets):
    now = datetime.datetime.utcnow().replace(microsecond=0)
    snippet = {
        'id': 3,
        'title': 'snippet #3',
        'changesets': [
            {'content': '(println "Hello, World!")'},
        ],
        'syntax': 'clojure',
        'tags': ['tag_b'],
        'created_at': now,
        'updated_at': now,
    }
    await testdatabase.snippets.insert([snippet])

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


async def _get_next_page(testapp, limit=3, marker=0):
    """"Helper function of traversing of the list of snippets via API."""

    params = []
    if limit:
        params.append('limit=%d' % limit)
    if marker:
        params.append('marker=%d' % marker)

    resp = await testapp.get(
        '/snippets' + ('?' if params else '') + '&'.join(params),
        headers={
            'Accept': 'application/json',
            # Pass the additional headers, that are set by nginx in the
            # production deployment, so that we ensure we generate the
            # correct links for users
            'Host': 'api.xsnippet.org',
            'X-Forwarded-Proto': 'https',
        }
    )
    assert resp.status == 200
    return resp


async def test_pagination_links(testapp, testdatabase):
    # Put 10 snippets into the db
    now = datetime.datetime.utcnow().replace(microsecond=0)
    snippets = [
        {
            'id': i + 1,
            'title': 'snippet #%d' % (i + 1),
            'changesets': [
                {'content': '(println "Hello, World!")'},
            ],
            'syntax': 'clojure',
            'tags': ['tag_b'],
            'created_at': (now + datetime.timedelta(seconds=1)),
            'updated_at': (now + datetime.timedelta(seconds=1)),
        }
        for i in range(10)
    ]
    await testdatabase.snippets.insert(snippets)

    # We should have seen snippets with ids 10, 9 and 8. No link to the prev
    # page, as we are at the very beginning of the list
    resp1 = await _get_next_page(testapp, limit=3)
    expected_link1 = (
        '<https://api.xsnippet.org/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/snippets?limit=3&marker=8>; rel="next"'
    )
    assert resp1.headers['Link'] == expected_link1
    assert [s['id'] for s in await resp1.json()] == [10, 9, 8]

    # We should have seen snippets with ids 7, 6 and 5. Prev page is the
    # beginning of the list, thus, no marker
    resp2 = await _get_next_page(testapp, limit=3, marker=8)
    expected_link2 = (
        '<https://api.xsnippet.org/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/snippets?limit=3&marker=5>; rel="next", '
        '<https://api.xsnippet.org/snippets?limit=3>; rel="prev"'
    )
    assert resp2.headers['Link'] == expected_link2
    assert [s['id'] for s in await resp2.json()] == [7, 6, 5]

    # We should have seen snippets with ids 4, 3 and 2
    resp3 = await _get_next_page(testapp, limit=3, marker=5)
    expected_link3 = (
        '<https://api.xsnippet.org/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/snippets?limit=3&marker=2>; rel="next", '
        '<https://api.xsnippet.org/snippets?limit=3&marker=8>; rel="prev"'
    )
    assert resp3.headers['Link'] == expected_link3
    assert [s['id'] for s in await resp3.json()] == [4, 3, 2]

    # We should have seen the snippet with id 1. No link to the next page,
    # as we have reached the end of the list
    resp4 = await _get_next_page(testapp, limit=3, marker=2)
    expected_link4 = (
        '<https://api.xsnippet.org/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/snippets?limit=3&marker=5>; rel="prev"'
    )
    assert resp4.headers['Link'] == expected_link4
    assert [s['id'] for s in await resp4.json()] == [1]


async def test_pagination_links_one_page_larger_than_whole_list(testapp, testdatabase):
    # Put 10 snippets into the db
    now = datetime.datetime.utcnow().replace(microsecond=0)
    snippets = [
        {
            'id': i + 1,
            'title': 'snippet #%d' % (i + 1),
            'changesets': [
                {'content': '(println "Hello, World!")'},
            ],
            'syntax': 'clojure',
            'tags': ['tag_b'],
            'created_at': (now + datetime.timedelta(seconds=1)),
            'updated_at': (now + datetime.timedelta(seconds=1)),
        }
        for i in range(10)
    ]
    await testdatabase.snippets.insert(snippets)

    # Default limit is 20 and there no prev/next pages - only the first one
    resp = await _get_next_page(testapp, limit=None)
    expected_link = '<https://api.xsnippet.org/snippets?limit=20>; rel="first"'
    assert resp.headers['Link'] == expected_link
    assert [s['id'] for s in await resp.json()] == list(reversed(range(1, 11)))


async def test_pagination_links_port_value_is_preserved_in_url(testapp):
    # Port is omitted
    resp1 = await testapp.get(
        '/snippets',
        headers={
            'Accept': 'application/json',
            # Pass the additional headers, that are set by nginx in the
            # production deployment, so that we ensure we generate the
            # correct links for users
            'Host': 'api.xsnippet.org',
            'X-Forwarded-Proto': 'https',
        }
    )
    expected_link1 = '<https://api.xsnippet.org/snippets?limit=20>; rel="first"'
    assert resp1.headers['Link'] == expected_link1

    # Port is passed explicitly
    resp2 = await testapp.get(
        '/snippets',
        headers={
            'Accept': 'application/json',
            # Pass the additional headers, that are set by nginx in the
            # production deployment, so that we ensure we generate the
            # correct links for users
            'Host': 'api.xsnippet.org:443',
            'X-Forwarded-Proto': 'https',
        }
    )
    expected_link2 = '<https://api.xsnippet.org:443/snippets?limit=20>; rel="first"'
    assert resp2.headers['Link'] == expected_link2


async def test_pagination_links_num_of_items_is_multiple_of_pages(testapp, testdatabase):
    # Put 12 snippets into the db
    now = datetime.datetime.utcnow().replace(microsecond=0)
    snippets = [
        {
            'id': i + 1,
            'title': 'snippet #%d' % (i + 1),
            'changesets': [
                {'content': '(println "Hello, World!")'},
            ],
            'syntax': 'clojure',
            'tags': ['tag_b'],
            'created_at': (now + datetime.timedelta(seconds=1)),
            'updated_at': (now + datetime.timedelta(seconds=1)),
        }
        for i in range(12)
    ]
    await testdatabase.snippets.insert(snippets)

    # We should have seen snippets with ids 12, 11, 10 and 9. No link to the
    # prev page, as we are at the very beginning of the list
    resp1 = await _get_next_page(testapp, limit=4)
    expected_link1 = (
        '<https://api.xsnippet.org/snippets?limit=4>; rel="first", '
        '<https://api.xsnippet.org/snippets?limit=4&marker=9>; rel="next"'
    )
    assert resp1.headers['Link'] == expected_link1
    assert [s['id'] for s in await resp1.json()] == [12, 11, 10, 9]

    # We should have seen snippets with ids 8, 7, 6 and 5. Link to the prev
    # page is a link to the beginning of the list
    resp2 = await _get_next_page(testapp, limit=4, marker=9)
    expected_link2 = (
        '<https://api.xsnippet.org/snippets?limit=4>; rel="first", '
        '<https://api.xsnippet.org/snippets?limit=4&marker=5>; rel="next", '
        '<https://api.xsnippet.org/snippets?limit=4>; rel="prev"'
    )
    assert resp2.headers['Link'] == expected_link2
    assert [s['id'] for s in await resp2.json()] == [8, 7, 6, 5]

    # We should have seen snippets with ids 4, 3, 2 and 1. Link to the next
    # page is not rendered, as we reached the end of the list
    resp3 = await _get_next_page(testapp, limit=4, marker=5)
    expected_link3 = (
        '<https://api.xsnippet.org/snippets?limit=4>; rel="first", '
        '<https://api.xsnippet.org/snippets?limit=4&marker=9>; rel="prev"'
    )
    assert resp3.headers['Link'] == expected_link3
    assert [s['id'] for s in await resp3.json()] == [4, 3, 2, 1]


async def test_pagination_links_non_consecutive_ids(testapp, testdatabase):
    now = datetime.datetime.utcnow().replace(microsecond=0)
    snippets = [
        {
            'id': i,
            'title': 'snippet #%d' % i,
            'changesets': [
                {'content': '(println "Hello, World!")'},
            ],
            'syntax': 'clojure',
            'tags': ['tag_b'],
            'created_at': (now + datetime.timedelta(seconds=1)),
            'updated_at': (now + datetime.timedelta(seconds=1)),
        }
        for i in [1, 7, 17, 23, 24, 29, 31, 87, 93, 104]
    ]
    await testdatabase.snippets.insert(snippets)

    resp1 = await _get_next_page(testapp, limit=3)
    expected_link1 = (
        '<https://api.xsnippet.org/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/snippets?limit=3&marker=87>; rel="next"'
    )
    assert resp1.headers['Link'] == expected_link1
    assert [s['id'] for s in await resp1.json()] == [104, 93, 87]

    resp2 = await _get_next_page(testapp, limit=3, marker=87)
    expected_link2 = (
        '<https://api.xsnippet.org/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/snippets?limit=3&marker=24>; rel="next", '
        '<https://api.xsnippet.org/snippets?limit=3>; rel="prev"'
    )
    assert resp2.headers['Link'] == expected_link2
    assert [s['id'] for s in await resp2.json()] == [31, 29, 24]

    resp3 = await _get_next_page(testapp, limit=3, marker=24)
    expected_link3 = (
        '<https://api.xsnippet.org/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/snippets?limit=3&marker=7>; rel="next", '
        '<https://api.xsnippet.org/snippets?limit=3&marker=87>; rel="prev"'
    )
    assert resp3.headers['Link'] == expected_link3
    assert [s['id'] for s in await resp3.json()] == [23, 17, 7]

    resp4 = await _get_next_page(testapp, limit=3, marker=7)
    expected_link4 = (
        '<https://api.xsnippet.org/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/snippets?limit=3&marker=24>; rel="prev"'
    )
    assert resp4.headers['Link'] == expected_link4
    assert [s['id'] for s in await resp4.json()] == [1]


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


async def test_post_snippet(testapp, testdatabase):
    resp = await testapp.post(
        '/snippets',
        data=json.dumps({
            'title': 'snippet #1',
            'content': 'def foo(): pass',
            'syntax': 'python',
            'tags': ['tag_a', 'tag_b'],
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    assert resp.status == 201

    snippet_resp = await resp.json()
    snippet_db = await testdatabase.snippets.find_one(
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
    snippet['content'] = snippets[0]['changesets'][0]['content']
    for key in ('id', 'created_at', 'updated_at', 'changesets'):
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
    assert re.match('`%s` - .*' % name, error_resp['message'])


async def test_post_snippet_syntax_enum_allowed(testapp, testconf, testdatabase):
    testconf['snippet']['syntaxes'] = 'python\nclojure'

    resp = await testapp.post(
        '/snippets',
        data=json.dumps({
            'content': 'test',
            'syntax': 'python',
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    assert resp.status == 201

    snippet_resp = await resp.json()
    snippet_db = await testdatabase.snippets.find_one(
        {'_id': snippet_resp['id']}
    )

    _compare_snippets(snippet_db, snippet_resp)


async def test_post_snippet_syntax_enum_not_allowed(testapp, testconf):
    testconf['snippet']['syntaxes'] = 'python\nclojure'

    resp = await testapp.post(
        '/snippets',
        data=json.dumps({
            'content': 'test',
            'syntax': 'go',
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    assert resp.status == 400

    error_resp = await resp.json()
    assert re.match('`syntax` - .*', error_resp['message'])


async def test_data_model_indexes_exist(testapp, testdatabase):
    res = await testdatabase.snippets.index_information()

    assert res['title_idx']['key'] == [('title', 1)]
    assert res['title_idx']['partialFilterExpression'] == {
        'title': {'$type': 'string'}
    }
    assert res['tags_idx']['key'] == [('tags', 1)]
    assert res['updated_id_idx']['key'] == [('updated_at', -1), ('_id', -1)]
    assert res['created_id_idx']['key'] == [('created_at', -1), ('_id', -1)]


async def test_get_snippet(testapp, snippets):
    awaited = copy.deepcopy(snippets[0])

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


async def test_delete_snippet(testapp, snippets):
    created = snippets[0]

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


async def test_put_snippet(testapp, testdatabase, snippets):
    resp = await testapp.put(
        '/snippets/' + str(snippets[0]['id']),
        data=json.dumps({
            'content': 'brand new snippet',
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    assert resp.status == 200

    snippet_resp = await resp.json()
    snippet_db = await testdatabase.snippets.find_one(
        {'_id': snippet_resp['id']}
    )

    _compare_snippets(snippet_db, snippet_resp)


async def test_put_snippet_bad_id(testapp):
    resp = await testapp.put(
        '/snippets/deadbeef',
        data=json.dumps({
            'content': 'brand new snippet',
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
    )
    assert resp.status == 400
    assert await resp.json() == {
        'message': '`id` - must be of integer type.'
    }


async def test_put_snippet_not_found(testapp):
    resp = await testapp.put(
        '/snippets/0123456789',
        data=json.dumps({
            'content': 'brand new snippet',
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
    )
    assert resp.status == 404
    assert await resp.json() == {
        'message': 'Sorry, cannot find the requested snippet.',
    }


@pytest.mark.parametrize('name, val', [
    ('title', 42),                          # must be string
    ('content', 42),                        # must be string
    ('tags', ['a tag with whitespaces']),   # tag must not contain spaces
    ('created_at', '2016-09-11T19:07:43'),  # readonly
    ('updated_at', '2016-09-11T19:07:43'),  # readonly
    ('non-existent-key', 'must not be accepted'),
])
async def test_put_snippet_malformed_snippet(name, val, testapp, snippets):
    snippet = {'content': 'brand new snippet'}
    snippet[name] = val

    resp = await testapp.put(
        '/snippets/' + str(snippets[0]['id']),
        data=json.dumps(snippet),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    assert resp.status == 400

    error_resp = await resp.json()
    assert re.match('`%s` - .*' % name, error_resp['message'])


@pytest.mark.parametrize('name', [
    'content',
])
async def test_put_snippet_required_fields(name, testapp, snippets):
    snippet = copy.deepcopy(snippets[0])
    snippet['content'] = snippet['changesets'][-1]['content']
    for key in ('id', 'created_at', 'updated_at', 'changesets'):
        del snippet[key]
    del snippet[name]

    resp = await testapp.put(
        '/snippets/' + str(snippets[0]['id']),
        data=json.dumps(snippet),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    assert resp.status == 400

    error_resp = await resp.json()
    assert re.match(
        '`%s` - required field.' % name, error_resp['message'])


async def test_put_snippet_syntax_enum_allowed(testapp, testconf, testdatabase, snippets):
    testconf['snippet']['syntaxes'] = 'python\nclojure'

    resp = await testapp.put(
        '/snippets/' + str(snippets[0]['id']),
        data=json.dumps({
            'content': 'brand new snippet',
            'syntax': 'python',
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    assert resp.status == 200

    snippet_resp = await resp.json()
    snippet_db = await testdatabase.snippets.find_one(
        {'_id': snippet_resp['id']}
    )
    _compare_snippets(snippet_db, snippet_resp)


async def test_put_snippet_syntax_enum_not_allowed(testapp, testconf, snippets):
    testconf['snippet']['syntaxes'] = 'python\nclojure'

    resp = await testapp.put(
        '/snippets/' + str(snippets[0]['id']),
        data=json.dumps({
            'content': 'brand new snippet',
            'syntax': 'go',
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    assert resp.status == 400

    error_resp = await resp.json()
    assert re.match(
        '`syntax` - unallowed value go.', error_resp['message'])


async def test_patch_snippet(testapp, testdatabase, snippets):
    resp = await testapp.patch(
        '/snippets/' + str(snippets[0]['id']),
        data=json.dumps({
            'content': 'brand new snippet',
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    assert resp.status == 200

    snippet_resp = await resp.json()
    snippet_db = await testdatabase.snippets.find_one(
        {'_id': snippet_resp['id']}
    )
    _compare_snippets(snippet_db, snippet_resp)


async def test_patch_snippet_bad_id(testapp):
    resp = await testapp.patch(
        '/snippets/deadbeef',
        data=json.dumps({
            'content': 'brand new snippet',
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
    )
    assert resp.status == 400
    assert await resp.json() == {
        'message': '`id` - must be of integer type.'
    }


async def test_patch_snippet_not_found(testapp):
    resp = await testapp.patch(
        '/snippets/0123456789',
        data=json.dumps({
            'content': 'brand new snippet',
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
    )
    assert resp.status == 404
    assert await resp.json() == {
        'message': 'Sorry, cannot find the requested snippet.',
    }


@pytest.mark.parametrize('name, value', [
    ('title', 42),                          # must be string
    ('content', 42),                        # must be string
    ('tags', ['a tag with whitespaces']),   # tag must not contain spaces
    ('created_at', '2016-09-11T19:07:43'),  # readonly
    ('updated_at', '2016-09-11T19:07:43'),  # readonly
    ('non-existent-key', 'must not be accepted'),
])
async def test_patch_snippet_malformed_snippet(name, value, testapp, snippets):

    snippet = {'content': 'brand new snippet'}
    snippet[name] = value

    resp = await testapp.patch(
        '/snippets/' + str(snippets[0]['id']),
        data=json.dumps(snippet),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    assert resp.status == 400

    error_resp = await resp.json()
    assert re.match('`%s` - .*' % name, error_resp['message'])


async def test_patch_snippet_required_fields_are_not_forced(testapp, testdatabase, snippets):
    resp = await testapp.patch(
        '/snippets/' + str(snippets[0]['id']),
        data=json.dumps({
            'title': 'brand new snippet',
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    assert resp.status == 200

    snippet_resp = await resp.json()
    snippet_db = await testdatabase.snippets.find_one(
        {'_id': snippet_resp['id']}
    )
    _compare_snippets(snippet_db, snippet_resp)


async def test_patch_snippet_syntax_enum_allowed(testapp, testconf, testdatabase, snippets):
    testconf['snippet']['syntaxes'] = 'python\nclojure'

    resp = await testapp.patch(
        '/snippets/' + str(snippets[0]['id']),
        data=json.dumps({
            'content': 'brand new snippet',
            'syntax': 'python',
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    assert resp.status == 200

    snippet_resp = await resp.json()
    snippet_db = await testdatabase.snippets.find_one(
        {'_id': snippet_resp['id']}
    )

    _compare_snippets(snippet_db, snippet_resp)


async def test_patch_snippet_syntax_enum_not_allowed(testapp, testconf, snippets):
    testconf['snippet']['syntaxes'] = 'python\nclojure'

    resp = await testapp.patch(
        '/snippets/' + str(snippets[0]['id']),
        data=json.dumps({
            'content': 'brand new snippet',
            'syntax': 'go',
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    assert resp.status == 400

    error_resp = await resp.json()
    assert re.match(
        '`syntax` - unallowed value go.', error_resp['message'])


@pytest.mark.parametrize('method', [
    'put',
    'patch',
    'delete',
])
async def test_snippet_update_is_not_exposed(method, testapp, testconf, snippets):
    testconf.remove_option('test', 'sudo')
    request = getattr(testapp, method)

    resp = await request(
        '/snippets/' + str(snippets[0]['id']),
        data=json.dumps({
            'content': 'brand new snippet',
            'syntax': 'go',
        }),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
    assert resp.status == 403

    error_resp = await resp.json()
    assert error_resp['message'] == 'Not yet. :)'
