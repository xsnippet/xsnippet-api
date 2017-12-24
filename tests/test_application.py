"""
    tests.test_application
    ----------------------

    Tests XSnippet application nuances.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import pytest
import pkg_resources

from xsnippet.api import application, conf
from xsnippet.api.middlewares import auth


@pytest.fixture(scope='function')
async def testapp(test_client):
    app_conf = conf.get_conf(
        pkg_resources.resource_filename('xsnippet.api', 'default.conf'))
    app_conf['auth'] = {'secret': 'SWORDFISH'}
    return await test_client(application.create_app(app_conf))


async def test_auth_secret_is_generated_if_not_set(test_server):
    app_conf = conf.get_conf(
        pkg_resources.resource_filename('xsnippet.api', 'default.conf'))
    app_conf['auth'] = {'secret': ''}
    app_instance = application.create_app(app_conf)

    await test_server(app_instance)
    assert len(app_instance['conf']['auth']['secret']) == auth.SECRET_LEN


@pytest.mark.parametrize('name, value', [
    ('Accept', 'application/json'),
    ('Accept-Encoding', 'gzip'),
    ('Api-Version', '1.0'),
])
async def test_http_vary_header(name, value, testapp):
    resp = await testapp.get('/', headers={
        name: value,
    })

    parts = set([
        hdr.strip() for hdr in resp.headers['Vary'].split(',')
    ])

    assert name in parts
    await resp.release()
