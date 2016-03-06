"""
    tests.resources.test_resource
    -----------------------------

    Tests base Resource class.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import json
import pkg_resources

from xsnippet_api.application import create_app
from xsnippet_api.conf import get_conf
from xsnippet_api.resources import resource
from tests import AIOTestMeta, AIOTestApp


class TestResource(metaclass=AIOTestMeta):

    class MyResource(resource.Resource):

        async def get(self):
            return self.make_response({'who': 'batman'}, status=299)

        async def post(self):
            data = await self.read_request()
            return self.make_response(data, status=298)

    def setup(self):
        conf = get_conf(
            pkg_resources.resource_filename('xsnippet_api', 'default.conf')
        )

        self.app = create_app(conf)
        self.app.router.add_route('*', '/test', self.MyResource)

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

            # NOTE: do not check response content, since it's not clear
            # whether should we respond with JSON or plain/text due to
            # the fact requested format is not supported.
            assert resp.status == 406
            resp.close()

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

            # TODO: check response message, it should be formatted with
            # 'acceptable' media type or plain/text otherwise
            assert resp.status == 415
            resp.close()

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

            # NOTE: do not check response content, since it's not clear
            # whether should we respond with JSON or plain/text due to
            # the fact requested format is not supported.
            assert resp.status == 406
            resp.close()
