"""
    tests.test_router
    -----------------

    Tests router module.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import pytest

from aiohttp import web
from xsnippet.api import router


@pytest.fixture(scope='function')
async def testapp(aiohttp_client):
    class _TestResource1(web.View):
        async def get(self):
            return web.Response(text='I am the night!')

    class _TestResource2(web.View):
        async def get(self):
            return web.Response(text='I am Batman!')

    router_v1 = web.UrlDispatcher()
    router_v1.add_route('*', '/test', _TestResource1)

    router_v2 = web.UrlDispatcher()
    router_v2.add_route('*', '/test', _TestResource2)

    app = web.Application(
        router=router.VersionRouter(
            {
                '1': router_v1,
                '2': router_v2,
            },
            default='2',
        )
    )
    return await aiohttp_client(app)


async def test_version_1(testapp):
    resp = await testapp.get('/test', headers={
        'Api-Version': '1',
    })

    assert resp.status == 200
    assert await resp.text() == 'I am the night!'


async def test_version_2(testapp):
    resp = await testapp.get('/test', headers={
        'Api-Version': '2',
    })

    assert resp.status == 200
    assert await resp.text() == 'I am Batman!'


async def test_version_is_not_passed(testapp):
    resp = await testapp.get('/test')

    assert resp.status == 200
    assert await resp.text() == 'I am Batman!'


async def test_version_is_incorrect(testapp):
    resp = await testapp.get('/test', headers={
        'Api-Version': '42',
    })

    async with resp:
        assert resp.status == 406
