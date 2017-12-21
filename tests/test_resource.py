"""
    tests.test_resource
    -------------------

    Tests base Resource class.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import json

import aiohttp.web as web
import pkg_resources

from xsnippet.api import conf, database, resource
from tests import AIOTestMeta, AIOTestApp


class _TestResource(resource.Resource):

    async def get(self):
        return self.make_response({'who': 'batman'}, status=299)

    async def post(self):
        data = await self.read_request()
        return self.make_response(data, status=298)


class TestResource(metaclass=AIOTestMeta):

    conf = conf.get_conf(
        pkg_resources.resource_filename('xsnippet.api', 'default.conf'))

    def setup(self):
        self.app = web.Application()
        self.app['db'] = database.create_connection(self.conf)

        self.app.router.add_route('*', '/test', _TestResource)

    async def test_get_json(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get('/test', headers={
                'Accept': 'application/json',
            })

            assert resp.status == 299
            assert await resp.json() == {'who': 'batman'}

    async def test_get_unsupported_media_type(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get('/test', headers={
                'Accept': 'application/mytype',
            })

            # NOTE: Do not check response context, since it's not clear
            # whether should we respond with JSON or plain/text or something
            # else due to the fact that requested format is not supported.
            async with resp:
                assert resp.status == 406

    async def test_post_json(self):
        async with AIOTestApp(self.app) as testapp:
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

    async def test_post_unsupported_media_type(self):
        async with AIOTestApp(self.app) as testapp:
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

    async def test_post_json_expect_unsupported_media_type(self):
        async with AIOTestApp(self.app) as testapp:
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
