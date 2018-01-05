"""
    tests.test_resource
    -------------------

    Tests base Resource class.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import json

import aiohttp.web as web
import pytest

from xsnippet.api import resource


class _TestResource(resource.Resource):

    async def get(self):
        return {'who': 'batman'}, 299

    async def post(self):
        data = await self.request.get_data()
        return data, 298


@pytest.fixture(scope='function')
async def testapp(test_client):
    app = web.Application()
    app['db'] = None
    app.router.add_route('*', '/test', _TestResource)
    return await test_client(app)


async def test_get_json(testapp):
    resp = await testapp.get('/test', headers={
        'Accept': 'application/json',
    })

    assert resp.status == 299
    assert await resp.json() == {'who': 'batman'}


async def test_get_unsupported_media_type(testapp):
    resp = await testapp.get('/test', headers={
        'Accept': 'application/mytype',
    })

    # NOTE: Do not check response context, since it's not clear
    # whether should we respond with JSON or plain/text or something
    # else due to the fact that requested format is not supported.
    async with resp:
        assert resp.status == 406


async def test_post_json(testapp):
    resp = await testapp.post(
        '/test',
        data=json.dumps({'who': 'batman'}),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
    )

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
