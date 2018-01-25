"""
    tests.test_resource
    -------------------

    Tests base Resource class.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import json
import collections

import aiohttp.web as web
import pytest

from xsnippet.api import resource


class _TestResource(resource.Resource):

    async def get(self):
        return {'who': 'batman'}, 299

    async def post(self):
        data = await self.request.get_data()
        return data, 298


class _TestEncodersResource(resource.Resource):

    _encoders = collections.OrderedDict([
        ('application/json', lambda _: 'application/json'),
        ('text/csv', lambda _: 'text/csv'),
        ('image/png', lambda _: 'image/png'),
    ])

    async def get(self):
        return {}


class _TestDecodersResource(resource.Resource):

    _encoders = collections.OrderedDict([
        ('text/plain', lambda text: text),
    ])

    _decoders = collections.OrderedDict([
        ('application/json', lambda _: 'application/json'),
        ('text/plain', lambda _: 'text/plain'),
    ])

    async def post(self):
        return await self.request.get_data()


@pytest.fixture(scope='function')
async def testapp(test_client):
    app = web.Application()
    app.router.add_route('*', '/test', _TestResource)
    app.router.add_route('*', '/test-encoders', _TestEncodersResource)
    app.router.add_route('*', '/test-decoders', _TestDecodersResource)

    # If 'Content-Type' is not passed to HTTP request, aiohttp client will
    # report 'Content-Type: text/plain' to server. This is completely
    # ridiculous because in case of RESTful API this is completely wrong
    # and APIs usually have their own defaults. So turn off this feature,
    # and do not set 'Content-Type' for us if it wasn't passed.
    return await test_client(app, skip_auto_headers={'Content-Type'})


@pytest.mark.parametrize('headers,', [
    {'Accept': 'application/json'},
    {'Accept': 'application/*'},
    {'Accept': '*/*'},
    {},
])
async def test_get_json(testapp, headers):
    resp = await testapp.get('/test', headers=headers)

    assert resp.status == 299
    assert await resp.json() == {'who': 'batman'}


@pytest.mark.parametrize('headers', [
    {'Accept': 'application/mytype'},
    {'Accept': 'foobar/json'},
])
async def test_get_unsupported_media_type(testapp, headers):
    resp = await testapp.get('/test', headers=headers)

    # NOTE: Do not check response context, since it's not clear
    # whether should we respond with JSON or plain/text or something
    # else due to the fact that requested format is not supported.
    async with resp:
        assert resp.status == 406


@pytest.mark.parametrize('accept, best_match', [
    ('text/csv; q=0.9, application/json',
     'application/json'),
    ('application/json; q=0.9, text/csv',
     'text/csv'),
    ('application/json; q=0.9, image/png, text/csv',
     'text/csv'),
    ('application/json; q=0.9, image/png; q=0.8, text/csv',
     'text/csv'),
    ('application/json; q=0.9, image/png; q=0.8, text/csv; q=1',
     'text/csv'),
    ('application/json; q=1, image/png; q=0.8, text/csv',
     'application/json'),
    ('application/json; q=0.4, image/png; q=0.3, text/csv; q=0.45',
     'text/csv'),
    ('text/plain, application/json; q=0.8',
     'application/json'),
    ('application/*, text/csv',
     'text/csv'),
    ('application/*, text/csv; q=0.9',
     'application/json'),
    ('text/*, application/yaml',
     'text/csv')
])
async def test_get_best_mimetype(testapp, accept, best_match):
    resp = await testapp.get('/test-encoders', headers={'Accept': accept})

    assert resp.status == 200
    assert await resp.text() == best_match


@pytest.mark.parametrize('content_type, best_match', [
    ('application/json', 'application/json'),
    ('text/plain', 'text/plain'),
    ('text/plain; format=fixed', 'text/plain'),
])
async def test_get_decoders(testapp, content_type, best_match):
    resp = await testapp.post('/test-decoders', headers={'Content-Type': content_type})

    assert resp.status == 200
    assert await resp.text() == best_match


@pytest.mark.parametrize('headers', [
    {'Accept': 'application/json', 'Content-Type': 'application/json'},
    {'Accept': 'application/json'},
    {},
])
async def test_post_json(testapp, headers):
    resp = await testapp.post('/test', data=json.dumps({'who': 'batman'}), headers=headers)

    assert resp.status == 298
    assert await resp.json() == {'who': 'batman'}


async def test_post_unsupported_media_type(testapp):
    resp = await testapp.post(
        '/test',
        data=json.dumps({'who': 'batman'}),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/mytype',
        }
    )

    async with resp:
        assert resp.status == 415


async def test_post_json_expect_unsupported_media_type(testapp):
    resp = await testapp.post(
        '/test',
        data=json.dumps({'who': 'batman'}),
        headers={
            'Accept': 'application/mytype',
            'Content-Type': 'application/json',
        }
    )

    # NOTE: Do not check response context, since it's not clear
    # whether should we respond with JSON or plain/text or something
    # else due to the fact that requested format is not supported.
    async with resp:
        assert resp.status == 406
