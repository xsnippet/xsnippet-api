"""
    xsnippet.api.__main__
    ---------------------

    The module contains application runner that starts XSnippet API
    instance.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import binascii
import logging
import os
import sys
import warnings

import aiohttp.web as web
import picobox

from xsnippet.api.application import create_app
from xsnippet.api.conf import get_conf
from xsnippet.api.database import create_connection


def main(args=sys.argv[1:]):
    # write access/error logs to stderr
    logging.basicConfig()
    logging.getLogger('aiohttp').setLevel(logging.INFO)

    conf = get_conf([
        os.path.join(os.path.dirname(__file__), 'default.conf'),
    ], envvar='XSNIPPET_API_SETTINGS')
    database = create_connection(conf)

    # The secret is required to sign issued JWT tokens, therefore it's crucial
    # to warn about importance of settings secret before going production. The
    # only reason why we don't enforce it's setting is because we want the app
    # to fly (at least for development purpose) using defaults.
    if not conf['auth'].get('secret', ''):
        warnings.warn(
            'Auth secret has not been provided. Please generate a long random '
            'secret before going to production.')
        conf['auth']['secret'] = binascii.hexlify(os.urandom(32)).decode('ascii')

    with picobox.push(picobox.Box()) as box:
        box.put('conf', conf)
        box.put('database', database)

        web.run_app(
            create_app(conf, database),
            host=conf['server']['host'],
            port=int(conf['server']['port']),
            access_log_format=conf['server']['access_log_format']
        )


# let's make this module and xsnippet.api package to be executable, so
# anyone can run it  without entry_points' console script
if __name__ == '__main__':
    main()
