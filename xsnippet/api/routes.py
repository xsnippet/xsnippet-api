"""Routes of various API versions."""

import aiohttp.web as web

from . import resources


v1 = [
    web.route('*', '/snippets', resources.Snippets),
    web.route('*', '/snippets/{id}', resources.Snippet),
    web.route('*', '/syntaxes', resources.Syntaxes),
]
