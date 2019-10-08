"""Routes of various API versions."""

import aiohttp.web as web

from . import resources


v1 = [
    web.route("*", "/v1/snippets", resources.Snippets),
    web.route("*", "/v1/snippets/{id}", resources.Snippet),
    web.route("*", "/v1/syntaxes", resources.Syntaxes),
    # These routes are what we had before during era of API versioning through
    # HTTP header. Nowadays we prefer versioning through HTTP URI, but we want
    # to be good guys and provide these routes for a while and avoid breaking
    # the world.
    web.route("*", "/snippets", resources.Snippets),
    web.route("*", "/snippets/{id}", resources.Snippet),
    web.route("*", "/syntaxes", resources.Syntaxes),
]
