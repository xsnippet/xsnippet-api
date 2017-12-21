"""
    xsnippet.api.exceptions
    -----------------------

    The module contains a set of XSnipet's exceptions.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""


class XSnippetException(Exception):
    """Gotta catch 'em all! (c)"""


class SnippetNotFound(XSnippetException):
    """Snippet not found in database."""
