"""
    xsnippet_api.__main__
    ---------------------

    The module contains application runner that starts XSnippet API
    instance.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import sys

from aiohttp import web

from xsnippet_api.application import create_app


def main(args=sys.argv[1:]):
    web.run_app(create_app())


# let's make this module and git_pr package to be executable, so anyone
# can run it  without entry_points' console script
if __name__ == '__main__':
    main()
