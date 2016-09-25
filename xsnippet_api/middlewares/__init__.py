"""
    xsnippet_api.middlewares
    ----------------------

    The package contains various helper middlewares used by the application.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

from .auth import auth


__all__ = [
    'auth',
]
