"""
    xsnippet.wsgi
    ~~~~~~~~~~~~~

    WSGI application.

    :copyright: (c) 2014, XSnippet Team
    :license: BSD, see LICENSE for details
"""

from xsnippet import create_app
from xsnippet import settings


app = create_app(settings)
