"""
    tests.resources.test_snippets
    -----------------------------

    Tests Snippets resource.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import json
import datetime
import cgi
import urllib.parse

import pytest


class _pytest_link_header:
    """Assert that two HTTP Link headers are equal to each other."""

    @staticmethod
    def parse(link):
        rv = []

        for link in link.split(','):
            link, params = cgi.parse_header(link)
            link = link.lstrip('<').rstrip('>')

            parts = urllib.parse.urlsplit(link)
            query = urllib.parse.parse_qs(parts.query)

            rv.append((parts.scheme, parts.netloc, parts.path, query, params))

        # Dictionaries can't be compared by < and/or >, so we need to sort by
        # first three components (scheme, netloc, path) and optional "rel"
        # parameter because the latter usually uniquely defines a link.
        return sorted(rv, key=lambda i: (i[-1].get('rel'), i[:3]))

    def __init__(self, link):
        self._link = link

    def __eq__(self, actual):
        return self.parse(self._link) == self.parse(actual)

    def __repr__(self):
        return "'%s'" % self._link


@pytest.fixture(scope='function')
async def snippets(testdatabase):
    snippets = [
        {
            'title': 'snippet #1',
            'changesets': [
                {'content': 'def foo(): pass'},
            ],
            'syntax': 'python',
            'tags': ['tag_a', 'tag_b'],
            'created_at': datetime.datetime(2018, 1, 24, 22, 26, 35),
            'updated_at': datetime.datetime(2018, 1, 24, 22, 26, 35),
        },
        {
            'title': 'snippet #2',
            'changesets': [
                {'content': 'int do_something() {}'},
            ],
            'syntax': 'cpp',
            'tags': ['tag_c'],
            'created_at': datetime.datetime(2018, 1, 24, 22, 32, 7),
            'updated_at': datetime.datetime(2018, 1, 24, 22, 32, 7),
        },
    ]

    # Usually pymongo updates passed collection so it has generated IDs
    # in-place. However, due to our custom SON manipulators it's not the
    # case in our case, since one of them makes a shallow copy which
    # basically results in no changes in the updated documents.
    ids = await testdatabase.snippets.insert(snippets)

    for id_, snippet in zip(ids, snippets):
        # One of SON manipulators we use converts 'id' into '_id' during
        # inserts/updates, and vice versa during reads. That's why we use
        # human readable 'id' and not '_id'.
        snippet['id'] = id_

    return snippets


async def test_get_no_snippets(testapp):
    resp = await testapp.get('/v1/snippets')

    assert resp.status == 200
    assert await resp.json() == []


@pytest.mark.parametrize('params, rv, link', [
    (
        {},
        [{'id': 2,
          'title': 'snippet #2',
          'content': 'int do_something() {}',
          'syntax': 'cpp',
          'tags': ['tag_c'],
          'created_at': '2018-01-24T22:32:07',
          'updated_at': '2018-01-24T22:32:07'},
         {'id': 1,
          'title': 'snippet #1',
          'content': 'def foo(): pass',
          'syntax': 'python',
          'tags': ['tag_a', 'tag_b'],
          'created_at': '2018-01-24T22:26:35',
          'updated_at': '2018-01-24T22:26:35'}],
        ('<https://api.xsnippet.org/v1/snippets?limit=20>; rel="first"'),
    ),
    (
        {'title': 'snippet #1'},
        [{'id': 1,
          'title': 'snippet #1',
          'content': 'def foo(): pass',
          'syntax': 'python',
          'tags': ['tag_a', 'tag_b'],
          'created_at': '2018-01-24T22:26:35',
          'updated_at': '2018-01-24T22:26:35'}],
        ('<https://api.xsnippet.org/v1/snippets?title=snippet+%231&limit=20>; rel="first"'),
    ),
    (
        {'title': 'nonexistent'},
        [],
        ('<https://api.xsnippet.org/v1/snippets?title=nonexistent&limit=20>; rel="first"'),
    ),
    (
        {'tag': 'tag_c'},
        [{'id': 2,
          'title': 'snippet #2',
          'content': 'int do_something() {}',
          'syntax': 'cpp',
          'tags': ['tag_c'],
          'created_at': '2018-01-24T22:32:07',
          'updated_at': '2018-01-24T22:32:07'}],
        ('<https://api.xsnippet.org/v1/snippets?tag=tag_c&limit=20>; rel="first"'),
    ),
    (
        {'tag': 'nonexistent'},
        [],
        ('<https://api.xsnippet.org/v1/snippets?tag=nonexistent&limit=20>; rel="first"'),
    ),
    (
        {'syntax': 'python'},
        [{'id': 1,
          'title': 'snippet #1',
          'content': 'def foo(): pass',
          'syntax': 'python',
          'tags': ['tag_a', 'tag_b'],
          'created_at': '2018-01-24T22:26:35',
          'updated_at': '2018-01-24T22:26:35'}],
        ('<https://api.xsnippet.org/v1/snippets?syntax=python&limit=20>; rel="first"'),
    ),
    (
        {'syntax': 'nonexistent'},
        [],
        ('<https://api.xsnippet.org/v1/snippets?syntax=nonexistent&limit=20>; rel="first"'),
    ),
    (
        {'syntax': 'cpp', 'tag': 'tag_c'},
        [{'id': 2,
          'title': 'snippet #2',
          'content': 'int do_something() {}',
          'syntax': 'cpp',
          'tags': ['tag_c'],
          'created_at': '2018-01-24T22:32:07',
          'updated_at': '2018-01-24T22:32:07'}],
        ('<https://api.xsnippet.org/v1/snippets?syntax=cpp&tag=tag_c&limit=20>; rel="first"'),
    ),
    (
        {'syntax': 'python', 'tag': 'tag_c'},
        [],
        ('<https://api.xsnippet.org/v1/snippets?syntax=python&tag=tag_c&limit=20>; rel="first"'),
    ),
    (
        {'limit': 1},
        [{'id': 2,
          'title': 'snippet #2',
          'content': 'int do_something() {}',
          'syntax': 'cpp',
          'tags': ['tag_c'],
          'created_at': '2018-01-24T22:32:07',
          'updated_at': '2018-01-24T22:32:07'}],
        ('<https://api.xsnippet.org/v1/snippets?limit=1>; rel="first", '
         '<https://api.xsnippet.org/v1/snippets?limit=1&marker=2>; rel="next"'),
    ),
    (
        {'marker': 2},
        [{'id': 1,
          'title': 'snippet #1',
          'content': 'def foo(): pass',
          'syntax': 'python',
          'tags': ['tag_a', 'tag_b'],
          'created_at': '2018-01-24T22:26:35',
          'updated_at': '2018-01-24T22:26:35'}],
        ('<https://api.xsnippet.org/v1/snippets?limit=20>; rel="first"'),
    ),
    (
        {'marker': 1},
        [],
        ('<https://api.xsnippet.org/v1/snippets?limit=20>; rel="first"'),
    ),
])
async def test_get_snippets(testapp, snippets, params, rv, link):
    resp = await testapp.get('/v1/snippets', params=params, headers={
        # Pass the additional headers, that are set by nginx in the production
        # deployment, so that we ensure we generate the correct links for
        # users.
        'Host': 'api.xsnippet.org',
        'X-Forwarded-Proto': 'https',
    })

    assert resp.status == 200
    assert await resp.json() == rv
    assert resp.headers['Link'] == _pytest_link_header(link)


@pytest.mark.parametrize('params, rv', [
    (
        {'title': ''},
        {'message': '`title` - empty values not allowed.'},
    ),
    (
        {'tag': ''},
        {'message': "`tag` - value does not match regex '[\\w_-]+'."},
    ),
    (
        {'tag': 'white space'},
        {'message': "`tag` - value does not match regex '[\\w_-]+'."},
    ),
    (
        {'syntax': ''},
        {'message': '`syntax` - unallowed value .'},
    ),
    (
        {'syntax': 'nonexistent'},
        {'message': '`syntax` - unallowed value nonexistent.'},
    ),
    (
        {'limit': 'deadbeef'},
        {'message': '`limit` - must be of integer type.'},
    ),
    (
        {'limit': '-1'},
        {'message': '`limit` - min value is 1.'},
    ),
    (
        {'deadbeef': 'joker'},
        {'message': '`deadbeef` - unknown field.'},
    ),
])
async def test_get_snippets_bad_request(testapp, testconf, snippets, params, rv):
    testconf['SNIPPET_SYNTAXES'] = ['python', 'clojure']

    resp = await testapp.get('/v1/snippets', params=params)

    assert resp.status == 400
    assert await resp.json() == rv


async def _get_next_page(testapp, limit=3, marker=0):
    """"Helper function of traversing of the list of snippets via API."""

    params = {}
    if limit:
        params['limit'] = limit
    if marker:
        params['marker'] = marker

    resp = await testapp.get('/v1/snippets', params=params, headers={
        # Pass the additional headers, that are set by nginx in the production
        # deployment, so that we ensure we generate the correct links for
        # users.
        'Host': 'api.xsnippet.org',
        'X-Forwarded-Proto': 'https',
    })
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
        '<https://api.xsnippet.org/v1/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/v1/snippets?limit=3&marker=8>; rel="next"'
    )
    assert resp1.headers['Link'] == expected_link1
    assert [s['id'] for s in await resp1.json()] == [10, 9, 8]

    # We should have seen snippets with ids 7, 6 and 5. Prev page is the
    # beginning of the list, thus, no marker
    resp2 = await _get_next_page(testapp, limit=3, marker=8)
    expected_link2 = (
        '<https://api.xsnippet.org/v1/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/v1/snippets?limit=3&marker=5>; rel="next", '
        '<https://api.xsnippet.org/v1/snippets?limit=3>; rel="prev"'
    )
    assert resp2.headers['Link'] == expected_link2
    assert [s['id'] for s in await resp2.json()] == [7, 6, 5]

    # We should have seen snippets with ids 4, 3 and 2
    resp3 = await _get_next_page(testapp, limit=3, marker=5)
    expected_link3 = (
        '<https://api.xsnippet.org/v1/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/v1/snippets?limit=3&marker=2>; rel="next", '
        '<https://api.xsnippet.org/v1/snippets?limit=3&marker=8>; rel="prev"'
    )
    assert resp3.headers['Link'] == expected_link3
    assert [s['id'] for s in await resp3.json()] == [4, 3, 2]

    # We should have seen the snippet with id 1. No link to the next page,
    # as we have reached the end of the list
    resp4 = await _get_next_page(testapp, limit=3, marker=2)
    expected_link4 = (
        '<https://api.xsnippet.org/v1/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/v1/snippets?limit=3&marker=5>; rel="prev"'
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
    expected_link = '<https://api.xsnippet.org/v1/snippets?limit=20>; rel="first"'
    assert resp.headers['Link'] == expected_link
    assert [s['id'] for s in await resp.json()] == list(reversed(range(1, 11)))


@pytest.mark.parametrize('protocol, host, link', [
    ('http', 'api.xsnippet.org',
     '<http://api.xsnippet.org/v1/snippets?limit=20>; rel="first"'),
    ('https', 'api.xsnippet.org',
     '<https://api.xsnippet.org/v1/snippets?limit=20>; rel="first"'),
    ('https', 'api.xsnippet.org:443',
     '<https://api.xsnippet.org:443/v1/snippets?limit=20>; rel="first"'),
])
async def test_pagination_link_respect_headers(testapp, protocol, host, link):
    resp = await testapp.get('/v1/snippets', headers={
        # Pass the additional headers, that are set by nginx in the production
        # deployment, so that we ensure we generate the correct links for
        # users.
        'Host': host,
        'X-Forwarded-Proto':  protocol,
    })

    assert resp.headers['Link'] == link


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
        '<https://api.xsnippet.org/v1/snippets?limit=4>; rel="first", '
        '<https://api.xsnippet.org/v1/snippets?limit=4&marker=9>; rel="next"'
    )
    assert resp1.headers['Link'] == expected_link1
    assert [s['id'] for s in await resp1.json()] == [12, 11, 10, 9]

    # We should have seen snippets with ids 8, 7, 6 and 5. Link to the prev
    # page is a link to the beginning of the list
    resp2 = await _get_next_page(testapp, limit=4, marker=9)
    expected_link2 = (
        '<https://api.xsnippet.org/v1/snippets?limit=4>; rel="first", '
        '<https://api.xsnippet.org/v1/snippets?limit=4&marker=5>; rel="next", '
        '<https://api.xsnippet.org/v1/snippets?limit=4>; rel="prev"'
    )
    assert resp2.headers['Link'] == expected_link2
    assert [s['id'] for s in await resp2.json()] == [8, 7, 6, 5]

    # We should have seen snippets with ids 4, 3, 2 and 1. Link to the next
    # page is not rendered, as we reached the end of the list
    resp3 = await _get_next_page(testapp, limit=4, marker=5)
    expected_link3 = (
        '<https://api.xsnippet.org/v1/snippets?limit=4>; rel="first", '
        '<https://api.xsnippet.org/v1/snippets?limit=4&marker=9>; rel="prev"'
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
        '<https://api.xsnippet.org/v1/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/v1/snippets?limit=3&marker=87>; rel="next"'
    )
    assert resp1.headers['Link'] == expected_link1
    assert [s['id'] for s in await resp1.json()] == [104, 93, 87]

    resp2 = await _get_next_page(testapp, limit=3, marker=87)
    expected_link2 = (
        '<https://api.xsnippet.org/v1/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/v1/snippets?limit=3&marker=24>; rel="next", '
        '<https://api.xsnippet.org/v1/snippets?limit=3>; rel="prev"'
    )
    assert resp2.headers['Link'] == expected_link2
    assert [s['id'] for s in await resp2.json()] == [31, 29, 24]

    resp3 = await _get_next_page(testapp, limit=3, marker=24)
    expected_link3 = (
        '<https://api.xsnippet.org/v1/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/v1/snippets?limit=3&marker=7>; rel="next", '
        '<https://api.xsnippet.org/v1/snippets?limit=3&marker=87>; rel="prev"'
    )
    assert resp3.headers['Link'] == expected_link3
    assert [s['id'] for s in await resp3.json()] == [23, 17, 7]

    resp4 = await _get_next_page(testapp, limit=3, marker=7)
    expected_link4 = (
        '<https://api.xsnippet.org/v1/snippets?limit=3>; rel="first", '
        '<https://api.xsnippet.org/v1/snippets?limit=3&marker=24>; rel="prev"'
    )
    assert resp4.headers['Link'] == expected_link4
    assert [s['id'] for s in await resp4.json()] == [1]


async def test_get_snippets_pagination_not_found(testapp):
    resp = await testapp.get(
        '/v1/snippets?limit=10&marker=1234567890',
        headers={
            'Accept': 'application/json',
        })
    assert resp.status == 404
    assert await resp.json() == {
        'message': 'Sorry, cannot complete the request since `marker` '
                   'points to a nonexistent snippet.',
    }


@pytest.mark.parametrize('snippet, rv', [
    ({'content': 'def foo(): pass'},
     {'id': 1,
      'title': None,
      'content': 'def foo(): pass',
      'syntax': None,
      'tags': [],
      'created_at': pytest.regex('\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'),
      'updated_at': pytest.regex('\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')}),

    ({'title': 'snippet #1',
      'content': 'def foo(): pass',
      'syntax': 'python',
      'tags': ['tag_a', 'tag_b']},
     {'id': 1,
      'title': 'snippet #1',
      'content': 'def foo(): pass',
      'syntax': 'python',
      'tags': ['tag_a', 'tag_b'],
      'created_at': pytest.regex('\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'),
      'updated_at': pytest.regex('\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')}),
])
async def test_post_snippet(testapp, testconf, snippet, rv):
    testconf['SNIPPET_SYNTAXES'] = ['python', 'clojure']

    resp = await testapp.post('/v1/snippets', data=json.dumps(snippet))

    assert resp.status == 201
    assert await resp.json() == rv


@pytest.mark.parametrize('snippet, rv', [
    (
        {},
        {'message': '`content` - required field.'},
    ),
    (
        {'content': 'test', 'title': 42},
        {'message': '`title` - must be of string type.'},
    ),
    (
        {'content': 42},
        {'message': '`content` - must be of string type.'},
    ),
    (
        {'content': ''},
        {'message': '`content` - empty values not allowed.'},
    ),
    (
        {'content': 'test', 'tags': ['white space']},
        {'message': '`tags` - {0: ["value does not match regex \'[\\\\w_-]+\'"]}.'},
    ),
    (
        {'content': 'test', 'created_at': '2016-09-11T19:07:43'},
        {'message': '`created_at` - field is read-only.'},
    ),
    (
        {'content': 'test', 'updated_at': '2016-09-11T19:07:43'},
        {'message': '`updated_at` - field is read-only.'},
    ),
    (
        {'content': 'test', 'non-existent-key': 'you-shall-not-pass'},
        {'message': '`non-existent-key` - unknown field.'},
    ),
    (
        {'content': 'test', 'syntax': 'go'},
        {'message': '`syntax` - unallowed value go.'},
    ),
])
async def test_post_snippet_bad_request(snippet, rv, testapp, testconf):
    testconf['SNIPPET_SYNTAXES'] = ['python', 'clojure']

    resp = await testapp.post('/v1/snippets', data=json.dumps(snippet))

    assert resp.status == 400
    assert await resp.json() == rv


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
    resp = await testapp.get('/v1/snippets/%d' % snippets[0]['id'])

    assert resp.status == 200
    assert await resp.json() == {
        'id': 1,
        'title': 'snippet #1',
        'content': 'def foo(): pass',
        'syntax': 'python',
        'tags': ['tag_a', 'tag_b'],
        'created_at': '2018-01-24T22:26:35',
        'updated_at': '2018-01-24T22:26:35',
    }


async def test_get_snippet_not_found(testapp):
    resp = await testapp.get('/v1/snippets/123456789')

    assert resp.status == 404
    assert await resp.json() == {'message': 'Sorry, cannot find the requested snippet.'}


async def test_get_snippet_bad_request(testapp):
    resp = await testapp.get('/v1/snippets/deadbeef')

    assert resp.status == 400
    assert await resp.json() == {'message': '`id` - must be of integer type.'}


async def test_delete_snippet(testapp, snippets):
    resp = await testapp.delete('/v1/snippets/%d' % snippets[0]['id'])

    assert resp.status == 204
    assert await resp.text() == ''


async def test_delete_snippet_not_found(testapp):
    resp = await testapp.delete('/v1/snippets/123456789')

    assert resp.status == 404
    assert await resp.json() == {'message': 'Sorry, cannot find the requested snippet.'}


async def test_delete_snippet_bad_request(testapp):
    resp = await testapp.delete('/v1/snippets/deadbeef')

    assert resp.status == 400
    assert await resp.json() == {'message': '`id` - must be of integer type.'}


@pytest.mark.parametrize('snippet, rv', [
    ({'content': 'def foo(): pass'},
     {'id': 1,
      'title': None,
      'content': 'def foo(): pass',
      'syntax': None,
      'tags': [],
      'created_at': pytest.regex('\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'),
      'updated_at': pytest.regex('\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')}),

    ({'title': 'snippet #1',
      'content': 'def foo(): pass',
      'syntax': 'python',
      'tags': ['tag_a', 'tag_b']},
     {'id': 1,
      'title': 'snippet #1',
      'content': 'def foo(): pass',
      'syntax': 'python',
      'tags': ['tag_a', 'tag_b'],
      'created_at': pytest.regex('\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'),
      'updated_at': pytest.regex('\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')}),
])
async def test_put_snippet(testapp, snippets, snippet, rv):
    resp = await testapp.put('/v1/snippets/1', data=json.dumps(snippet))

    assert resp.status == 200
    assert await resp.json() == rv


async def test_put_snippet_bad_id(testapp):
    resp = await testapp.put('/v1/snippets/deadbeef', data=json.dumps({'content': 'test'}))

    assert resp.status == 400
    assert await resp.json() == {'message': '`id` - must be of integer type.'}


async def test_put_snippet_not_found(testapp):
    resp = await testapp.put('/v1/snippets/123456789', data=json.dumps({'content': 'test'}))

    assert resp.status == 404
    assert await resp.json() == {'message': 'Sorry, cannot find the requested snippet.'}


@pytest.mark.parametrize('snippet, rv', [
    (
        {},
        {'message': '`content` - required field.'},
    ),
    (
        {'content': 'test', 'title': 42},
        {'message': '`title` - must be of string type.'},
    ),
    (
        {'content': 42},
        {'message': '`content` - must be of string type.'},
    ),
    (
        {'content': ''},
        {'message': '`content` - empty values not allowed.'},
    ),
    (
        {'content': 'test', 'tags': ['white space']},
        {'message': '`tags` - {0: ["value does not match regex \'[\\\\w_-]+\'"]}.'},
    ),
    (
        {'content': 'test', 'created_at': '2016-09-11T19:07:43'},
        {'message': '`created_at` - field is read-only.'},
    ),
    (
        {'content': 'test', 'updated_at': '2016-09-11T19:07:43'},
        {'message': '`updated_at` - field is read-only.'},
    ),
    (
        {'content': 'test', 'non-existent-key': 'you-shall-not-pass'},
        {'message': '`non-existent-key` - unknown field.'},
    ),
    (
        {'content': 'test', 'syntax': 'go'},
        {'message': '`syntax` - unallowed value go.'},
    ),
])
async def test_put_snippet_bad_request(snippet, rv, testapp, testconf, snippets):
    testconf['SNIPPET_SYNTAXES'] = ['python', 'clojure']

    resp = await testapp.put('/v1/snippets/%d' % snippets[0]['id'], data=json.dumps(snippet))

    assert resp.status == 400
    assert await resp.json() == rv


async def test_patch_snippet(testapp, snippets):
    resp = await testapp.patch('/v1/snippets/%d' % snippets[0]['id'], data=json.dumps({
        'content': 'test',
    }))

    assert resp.status == 200
    assert await resp.json() == {
        'id': 1,
        'title': 'snippet #1',
        'content': 'test',
        'syntax': 'python',
        'tags': ['tag_a', 'tag_b'],
        'created_at': '2018-01-24T22:26:35',
        'updated_at': pytest.regex('\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'),
    }


async def test_patch_snippet_bad_id(testapp):
    resp = await testapp.patch('/v1/snippets/deadbeef', data=json.dumps({'content': 'test'}))

    assert resp.status == 400
    assert await resp.json() == {'message': '`id` - must be of integer type.'}


async def test_patch_snippet_not_found(testapp):
    resp = await testapp.patch('/v1/snippets/123456789', data=json.dumps({'content': 'test'}))

    assert resp.status == 404
    assert await resp.json() == {'message': 'Sorry, cannot find the requested snippet.'}


@pytest.mark.parametrize('snippet, rv', [
    (
        {'title': 42},
        {'message': '`title` - must be of string type.'},
    ),
    (
        {'content': 42},
        {'message': '`content` - must be of string type.'},
    ),
    (
        {'content': ''},
        {'message': '`content` - empty values not allowed.'},
    ),
    (
        {'tags': ['white space']},
        {'message': '`tags` - {0: ["value does not match regex \'[\\\\w_-]+\'"]}.'},
    ),
    (
        {'created_at': '2016-09-11T19:07:43'},
        {'message': '`created_at` - field is read-only.'},
    ),
    (
        {'updated_at': '2016-09-11T19:07:43'},
        {'message': '`updated_at` - field is read-only.'},
    ),
    (
        {'non-existent-key': 'you-shall-not-pass'},
        {'message': '`non-existent-key` - unknown field.'},
    ),
    (
        {'syntax': 'go'},
        {'message': '`syntax` - unallowed value go.'},
    ),
])
async def test_patch_snippet_bad_request(snippet, rv, testapp, testconf, snippets):
    testconf['SNIPPET_SYNTAXES'] = ['python', 'clojure']

    resp = await testapp.patch('/v1/snippets/%d' % snippets[0]['id'], data=json.dumps(snippet))

    assert resp.status == 400
    assert await resp.json() == rv


@pytest.mark.parametrize('method', [
    'put',
    'patch',
    'delete',
])
async def test_snippet_update_is_not_exposed(method, testapp, testconf, snippets):
    testconf.pop('_SUDO', None)
    request = getattr(testapp, method)

    snippet = {'content': 'test'}
    resp = await request('/v1/snippets/%d' % snippets[0]['id'], data=json.dumps(snippet))

    assert resp.status == 403
    assert await resp.json() == {'message': 'Not yet. :)'}
