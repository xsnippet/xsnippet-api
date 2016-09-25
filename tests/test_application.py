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
        ('X-Api-Version', '1'),
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
            resp.close()
