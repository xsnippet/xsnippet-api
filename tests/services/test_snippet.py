"""
    tests.services.test_snippet
    ---------------------------

    Tests Snippet service.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import datetime
import operator

import pkg_resources
import pytest

from xsnippet.api.database import create_connection
from xsnippet.api.conf import get_conf
from xsnippet.api.services import Snippet
from xsnippet.api import exceptions


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


@pytest.fixture(scope='function')
async def db(loop, snippets, request):
    connection = create_connection(
        get_conf(
            pkg_resources.resource_filename('xsnippet.api', 'default.conf')))

    await connection.snippets.remove()
    await connection.snippets.insert(snippets)

    # make sure all new documents won't collide with our fixture above
    await connection['_autoincrement_ids'].find_and_modify(
        query={'_id': 'snippets'},
        update={'$set': {'next': 2}},
        upsert=True
    )
    request.addfinalizer(
        lambda: loop.run_until_complete(connection.snippets.remove()))
    return connection


@pytest.fixture(scope='function')
async def testservice(db):
    return Snippet(db)


async def test_get_one(testservice, snippets):
    snippet = await testservice.get_one(snippets[0]['id'])
    assert snippet == snippets[0]


async def test_get_one_not_found(testservice):
    with pytest.raises(exceptions.SnippetNotFound) as excinfo:
        await testservice.get_one('whatever')
    excinfo.match(r'Sorry, cannot find the requested snippet.')


async def test_get(testservice, snippets):
    returned_snippets = await testservice.get()

    # Service layer returns snippets sorted in DESC order, so the
    # order is different. However, we don't care about order, we
    # are more interested in items.
    a = sorted(returned_snippets, key=operator.itemgetter('id'))
    b = sorted(snippets, key=operator.itemgetter('id'))

    assert a == b


async def test_get_limit(testservice, snippets):
    returned_snippets = await testservice.get(limit=1)

    # the last inserted snippet should be returned by service layer,
    # so prepare it for assertion
    snippet = snippets[-1]

    assert len(returned_snippets) == 1
    assert returned_snippets == [snippet]


async def test_get_pagination(testservice, snippets):
    snippet = {
        'title': 'my snippet',
        'content': '...',
        'syntax': 'python',
    }
    created = await testservice.create(snippet)

    one = await testservice.get(limit=1)
    assert len(one) == 1
    assert one == [created]

    two = await testservice.get(marker=one[0]['id'])
    assert len(two) == 2
    assert two == list(reversed(snippets))


async def test_get_pagination_not_found(testservice):
    with pytest.raises(exceptions.SnippetNotFound) as excinfo:
        await testservice.get(limit=10, marker=123456789)

    excinfo.match(r'Sorry, cannot complete the request since `marker` '
                  r'points to a nonexistent snippet.')


async def test_get_filter_by_title(testservice, snippets):
    result = await testservice.get(title='snippet #1')
    assert result == [snippets[0]]

    prefix_match = await testservice.get(title='snippet')
    assert prefix_match == list(reversed(snippets))

    regexes_are_escaped = await testservice.get(title='^snippet.*')
    assert regexes_are_escaped == []

    nonexistent = await testservice.get(title='non existing snippet')
    assert nonexistent == []


async def test_get_filter_by_tag(testservice, snippets):
    result = await testservice.get(tag='tag_c')
    assert result == [snippets[1]]

    with_multiple_tags = await testservice.get(tag='tag_a')
    assert with_multiple_tags == [snippets[0]]

    nonexistent = await testservice.get(tag='non_existing_tag')
    assert nonexistent == []


async def test_get_filter_by_title_and_tag(testservice, snippets):
    result = await testservice.get(title='snippet #2', tag='tag_c')
    assert result == [snippets[1]]

    nonexistent = await testservice.get(title='snippet #2', tag='tag_a')
    assert nonexistent == []


async def test_get_filter_by_title_and_tag_w_pagination(testservice, snippets):
    snippet = {
        'title': 'snippet #1',
        'content': '...',
        'syntax': 'python',
        'tags': ['tag_a']
    }
    created = await testservice.create(snippet)

    one = await testservice.get(title='snippet #1', tag='tag_a', limit=1)
    assert one == [created]

    another = await testservice.get(title='snippet #1', tag='tag_a',
                                    marker=one[0]['id'], limit=1)
    assert another == [snippets[0]]


async def test_create(testservice, db):
    snippet = {
        'title': 'my snippet',
        'content': '...',
        'syntax': 'python',
    }

    created = await testservice.create(snippet)
    created_db = await db.snippets.find_one(
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


async def test_delete(testservice, db, snippets):
    _id = snippets[0]['id']

    before = await db.snippets.find({}).to_list(None)
    assert len(before) == 2

    rv = await testservice.delete(_id)
    assert rv is None

    after = await db.snippets.find({}).to_list(None)
    assert len(after) == 1


async def test_delete_not_found(testservice):
    with pytest.raises(exceptions.SnippetNotFound) as excinfo:
        await testservice.delete(123456789)

    excinfo.match(r'Sorry, cannot find the requested snippet.')
