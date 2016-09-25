"""
    tests.middlewares.test_auth
    ---------------------------

    Tests XSnippet authentication middleware.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import functools

import aiohttp.web as web
import jose.jwt as jwt
import pytest

from xsnippet_api import middlewares
from tests import AIOTestMeta, AIOTestApp


class TestAuthMiddleware(metaclass=AIOTestMeta):

    conf = {
        'auth': {
            'secret': 'SWORDFISH'
        }
    }

    def setup(self):
        async def handler(request):
            return web.Response(text='success')

        self.app = web.Application(middlewares=[
            functools.partial(middlewares.auth, self.conf['auth'])
        ])
        self.app.router.add_get('/', handler)

    @pytest.mark.parametrize('token', [
        'malformed_token_value',
        jwt.encode({'valid': 'token'}, 'wrong secret')
    ])
    async def test_unauthorized_is_raised_for_invalid_tokens(self, token):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get('/', headers={
                'X-Auth-Token': token
            })
            text = await resp.text()

            assert resp.status == 401
            assert 'passed token is invalid' in text

            resp.close()

    async def test_authentication_succeeds(self):
        async def handler(request):
            assert request['auth']['user'] == 'john'

            return web.Response(text='success')

        self.app.router.add_get('/test_auth', handler)

        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get('/test_auth', headers={
                'X-Auth-Token': jwt.encode({'user': 'john'}, 'SWORDFISH')
            })

            assert resp.status == 200

            resp.close()

    async def test_authentication_token_not_passed(self):
        async def handler(request):
            assert request['auth'] is None

            return web.Response(text='success')

        self.app.router.add_get('/test_auth', handler)

        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get('/test_auth')

            assert resp.status == 200

            resp.close()
