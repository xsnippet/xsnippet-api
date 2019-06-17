"""Some pytest fixtures used around the code."""

import re

import picobox
import pytest

from xsnippet.api.application import create_app
from xsnippet.api.conf import get_conf
from xsnippet.api.database import create_connection


@pytest.fixture(scope='function')
def testconf():
    conf = get_conf()
    conf['AUTH_SECRET'] = 'SWORDFISH'

    # This flag exist to workaround permissions (which we currently lack of)
    # and test PUT/PATCH requests to the snippet. Once permissions are
    # implemented and the hack is removed from @checkpermissions decorator
    # in resources/snippets.py - this silly flag must be thrown away.
    conf['_SUDO'] = True
    return conf


@pytest.fixture(scope='function')
async def testdatabase(request, loop, testconf):
    database = create_connection(testconf)

    # Python 3.5 does not support yield statement inside coroutines, hence we
    # cannot use yield fixtures here and are forced to use finalizers instead.
    request.addfinalizer(lambda: loop.run_until_complete(database.client.drop_database(database)))
    return database


@pytest.fixture(scope='function')
async def testapp(request, aiohttp_client, testconf, testdatabase):
    box = picobox.Box()
    box.put('conf', testconf)
    box.put('database', testdatabase)

    picobox.push(box)

    # Python 3.5 does not support yield statement inside coroutines, hence we
    # cannot use yield fixtures here and are forced to use finalizers instead.
    # This is especially weird as Picobox provides convenient context manager
    # and no plain functions, that's why manual triggering is required.
    request.addfinalizer(lambda: picobox.pop())
    return await aiohttp_client(
        create_app(),

        # If 'Content-Type' is not passed to HTTP request, aiohttp client will
        # report 'Content-Type: text/plain' to server. This is completely
        # ridiculous because in case of RESTful API this is completely wrong
        # and APIs usually have their own defaults. So turn off this feature,
        # and do not set 'Content-Type' for us if it wasn't passed.
        skip_auto_headers={'Content-Type'},
    )


def pytest_configure():
    # Expose some internally used helpers via 'pytest' module to make it
    # available everywhere without making modules and packages. We used
    # to have 'pytest_namespace' hook, however, it's been removed since
    # pytest 4.0 and thus we need this line for backward compatibility.
    pytest.regex = _pytest_regex


class _pytest_regex:
    """Assert that a given string matches a given regular expression."""

    def __init__(self, pattern, flags=0):
        self._regex = re.compile(pattern, flags)

    def __eq__(self, actual):
        return bool(self._regex.match(actual))

    def __repr__(self):
        return self._regex.pattern
