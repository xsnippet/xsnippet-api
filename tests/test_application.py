"""
    tests.test_application
    ----------------------

    Tests XSnippet application nuances.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import pytest
import pkg_resources

from xsnippet_api import application, conf
from xsnippet_api.middlewares import auth
from tests import AIOTestMeta, AIOTestApp


class TestApplication(metaclass=AIOTestMeta):

    conf = conf.get_conf(
        pkg_resources.resource_filename('xsnippet_api', 'default.conf'))
    conf['auth'] = {'secret': 'SWORDFISH'}

    def setup(self):
        self.app = application.create_app(self.conf)

    @pytest.mark.parametrize('name, value', [
        ('Accept', 'application/json'),
        ('Accept-Encoding', 'gzip'),
        ('Api-Version', '1.0'),
    ])
    async def test_http_vary_header(self, name, value):
        async with AIOTestApp(self.app) as testapp:
            resp = await testapp.get('/', headers={
                name: value,
            })

            parts = set([
                hdr.strip() for hdr in resp.headers['Vary'].split(',')
            ])

            assert name in parts
            await resp.release()

    async def test_auth_secret_is_generated_if_not_set(self):
        app_conf = conf.get_conf(
            pkg_resources.resource_filename('xsnippet_api', 'default.conf'))
        app_conf['auth'] = {'secret': ''}

        app = application.create_app(app_conf)
        async with AIOTestApp(app):
            assert len(app['conf']['auth']['secret']) == auth.SECRET_LEN
