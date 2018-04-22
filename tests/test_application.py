"""
    tests.test_application
    ----------------------

    Tests XSnippet application nuances.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import pytest

from xsnippet.api.application import create_app


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


async def test_deprecated_routes(testapp):
    app = create_app()

    def _extract_path(route):
        info = route.resource.get_info()
        return info.get('path') or info.get('formatter')
    routes = {_extract_path(route): route.handler for route in app.router.routes()}

    assert routes['/snippets'] is routes['/v1/snippets']
    assert routes['/snippets/{id}'] is routes['/v1/snippets/{id}']
    assert routes['/syntaxes'] is routes['/v1/syntaxes']
