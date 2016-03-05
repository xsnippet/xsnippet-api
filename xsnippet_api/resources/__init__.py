"""
    xsnippet_api.resources
    ----------------------

    The package contains implementations of RESTful API resources.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

from .snippets import Snippet, Snippets


__all__ = [
    'Snippet',
    'Snippets',
]
