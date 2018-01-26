"""Some pytest fixtures used around the code."""

import picobox
import pkg_resources
import pytest

from xsnippet.api.application import create_app
from xsnippet.api.conf import get_conf
from xsnippet.api.database import create_connection


@pytest.fixture(scope='function')
def testconf():
    path = pkg_resources.resource_filename('xsnippet.api', 'default.conf')
    conf = get_conf(path)
    conf['auth'] = {'secret': 'SWORDFISH'}

    # This flag exist to workaround permissions (which we currently lack of)
    # and test PUT/PATCH requests to the snippet. Once permissions are
    # implemented and the hack is removed from @checkpermissions decorator
    # in resources/snippets.py - this silly flag must be thrown away.
    conf['test'] = {'sudo': True}
    return conf


@pytest.fixture(scope='function')
async def testdatabase(request, loop, testconf):
    database = create_connection(testconf)

    # Python 3.5 does not support yield statement inside coroutines, hence we
    # cannot use yield fixtures here and are forced to use finalizers instead.
    request.addfinalizer(lambda: loop.run_until_complete(database.client.drop_database(database)))
    return database


@pytest.fixture(scope='function')
async def testapp(request, test_client, testconf, testdatabase):
    box = picobox.Box()
    box.put('conf', testconf)
    box.put('database', testdatabase)

    scope = picobox.push(box)
    scope.__enter__()

    # Python 3.5 does not support yield statement inside coroutines, hence we
    # cannot use yield fixtures here and are forced to use finalizers instead.
    # This is especially weird as Picobox provides convenient context manager
    # and no plain functions, that's why manual triggering is required.
    request.addfinalizer(lambda: scope.__exit__(None, None, None))
    return await test_client(
        create_app(),

        # If 'Content-Type' is not passed to HTTP request, aiohttp client will
        # report 'Content-Type: text/plain' to server. This is completely
        # ridiculous because in case of RESTful API this is completely wrong
        # and APIs usually have their own defaults. So turn off this feature,
        # and do not set 'Content-Type' for us if it wasn't passed.
        skip_auto_headers={'Content-Type'},
    )
