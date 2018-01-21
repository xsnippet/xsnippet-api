"""
    tests.middlewares.test_auth
    ---------------------------

    Tests XSnippet authentication middleware.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import aiohttp.web as web
import jose.jwt as jwt
import pytest

from xsnippet.api import middlewares


@pytest.fixture(scope='function')
async def testapp(test_client):
    app = web.Application(middlewares=[
        middlewares.auth.auth({'secret': 'SWORDFISH'}),
    ])

    async def handler(request):
        return web.Response(text='success')
    app.router.add_get('/', handler)

    async def handler(request):
        assert request['auth']['user'] == 'john'
        return web.Response(text='success')
    app.router.add_get('/success', handler)

    async def handler(request):
        assert request['auth'] is None
        return web.Response(text='success')
    app.router.add_get('/success-no-token', handler)

    return await test_client(app)


@pytest.mark.parametrize('token', [
    'malformed_token_value',
    jwt.encode({'valid': 'token'}, 'wrong secret')
])
async def test_unauthorized_is_raised_for_invalid_tokens(token, testapp):
    resp = await testapp.get('/', headers={
        'Authorization': 'bearer ' + token
    })

    assert resp.status == 401
    assert 'passed token is invalid' in await resp.text()


async def test_authentication_succeeds(testapp):
    token = jwt.encode({'user': 'john'}, 'SWORDFISH')
    resp = await testapp.get('/success', headers={
        'Authorization': 'bearer ' + token
    })

    async with resp:
        assert resp.status == 200


async def test_authentication_token_not_passed(testapp):
    resp = await testapp.get('/success-no-token')

    async with resp:
        assert resp.status == 200


async def test_unauthorized_is_raised_for_invalid_type(testapp):
    token = jwt.encode({'user': 'john'}, 'SWORDFISH')
    resp = await testapp.get('/', headers={
        'Authorization': 'token ' + token
    })

    assert resp.status == 401
    assert 'Unsupported auth type' in await resp.text()


@pytest.mark.parametrize('header, error', [
    ('bearer', 'Token missing'),
    ('bearer t oken', 'Token contains spaces'),
])
async def test_unauthorized_for_invalid_header(header, error, testapp):
    resp = await testapp.get('/', headers={
        'Authorization': header
    })

    assert resp.status == 401
    assert error in await resp.text()
