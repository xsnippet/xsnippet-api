"""
    tests.test_application
    ----------------------

    Tests XSnippet application nuances.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import pytest

from xsnippet.api import application
from xsnippet.api.middlewares import auth


async def test_auth_secret_is_generated_if_not_set(test_server, testconf, testdatabase):
    testconf['auth'] = {'secret': ''}
    app_instance = application.create_app(testconf, testdatabase)

    await test_server(app_instance)
    assert len(testconf['auth']['secret']) == auth.SECRET_LEN


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
