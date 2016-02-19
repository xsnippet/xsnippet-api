"""
    xsnippet_api.application
    ------------------------

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

from aiohttp import web


def get_application():
    app = web.Application()
    return app
