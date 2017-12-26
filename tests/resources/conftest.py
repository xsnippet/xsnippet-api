import pkg_resources
import pytest

from xsnippet.api.application import create_app
from xsnippet.api.conf import get_conf


@pytest.fixture(scope='function')
def appinstance():
    conf = get_conf(
        pkg_resources.resource_filename('xsnippet.api', 'default.conf'))
    conf['auth'] = {'secret': 'SWORDFISH'}
    return create_app(conf)


@pytest.fixture(scope='function')
async def db(testapp, appinstance):
    # It's important to depend on testapp, as it starts the app and we create
    # DB connection during startup.
    return appinstance['db']


@pytest.fixture(scope='function')
async def testapp(request, loop, appinstance, test_client):
    request.addfinalizer(
        lambda: loop.run_until_complete(appinstance['db'].snippets.remove()))
    return await test_client(appinstance)
