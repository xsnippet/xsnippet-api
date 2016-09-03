"""
    tests.test_router
    -----------------

    Tests router module.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import pytest

from aiohttp import web, web_urldispatcher
from xsnippet_api import router

from tests import AIOTestMeta, AIOTestApp


class TestVersionRouter(metaclass=AIOTestMeta):

    class _TestResource1(web.View):
        async def get(self):
            return web.Response(text='I am the night!')

    class _TestResource2(web.View):
        async def get(self):
            return web.Response(text='I am Batman!')

    def setup(self):
        router_v1 = web_urldispatcher.UrlDispatcher()
        router_v1.add_route('*', '/test', self._TestResource1)

        router_v2 = web_urldispatcher.UrlDispatcher()
        router_v2.add_route('*', '/test', self._TestResource2)

        self.app = web.Application(router=router.VersionRouter(
            {
                '1': router_v1,
                '2': router_v2,
            }
        ))

    async def test_version_1(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get('/test', headers={
                'X-Api-Version': '1',
            })

            assert resp.status == 200
            assert await resp.text() == 'I am the night!'

    async def test_version_2(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get('/test', headers={
                'X-Api-Version': '2',
            })

            assert resp.status == 200
            assert await resp.text() == 'I am Batman!'

    async def test_version_is_not_passed(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get('/test')

            assert resp.status == 200
            assert await resp.text() == 'I am Batman!'

    async def test_version_is_incorrect(self):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get('/test', headers={
                'X-Api-Version': '42',
            })

            assert resp.status == 412
            resp.close()


class TestGetLatestVersion:

    @pytest.mark.parametrize('versions, expected',  [
        (['1', '2', '3', '4'], '4'),
        (['4', '1', '3', '2'], '4'),
        (['1.1', '1.4', '1.10', '1.5'], '1.10'),
        (['1.1', '2.0', '1.10', '1.5'], '2.0'),
    ])
    def test_general_case(self, versions, expected):
        assert router._get_latest_version(versions) == expected

    @pytest.mark.parametrize('versions, expected',  [
        (['1', '1-alpha', '1-beta2', '1-dev13'], '1'),
        (['1', '2-alpha', '2-beta2', '2-dev13'], '1'),
    ])
    def test_pre_releases_are_ignored(self, versions, expected):
        assert router._get_latest_version(versions) == expected

    @pytest.mark.parametrize('versions, expected',  [
        (['1', '1-alpha', '1-beta2', '1-dev13'], '1'),
        (['1', '2-alpha', '2-beta2', '2-dev13'], '2-beta2'),
    ])
    def test_pre_releases_are_counted(self, versions, expected):
        assert router._get_latest_version(versions, False) == expected
