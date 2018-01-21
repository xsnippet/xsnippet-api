"""
    xsnippet.api.middlewares.auth
    -----------------------------

    The module implements auth middleware that performs authentication
    of user requests.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import random
import string

import aiohttp.web as web
import jose.jwt as jwt


SECRET_LEN = 64


async def setup(app, conf):
    """Perform middleware setup steps at application startup.

    E.g. generate a temporary secret, if one was not set in conf explicitly."""

    secret = conf['auth'].get('secret', '')
    if not secret:
        symbols = string.ascii_letters + string.digits
        secret = ''.join(random.choice(symbols) for _ in range(SECRET_LEN))

        conf['auth']['secret'] = secret


def auth(conf):
    """Authentication middleware.

    Performs user authentication by validating tokens passed in Authorization
    header. Tokens are expected to be in JSON Web Token (RFC 7519) format.

    On success the request object is modified to store an additional key 'auth'
    which points to the parsed token value.

    On failure 401 Unauthorized error is raised.
    """

    @web.middleware
    async def _auth(request, handler):
        secret = conf['secret']
        authorization = request.headers.get('Authorization')

        if authorization is not None:
            parts = authorization.strip().split()

            if parts[0].lower() != 'bearer':
                raise web.HTTPUnauthorized(reason='Unsupported auth type.')
            elif len(parts) == 1:
                raise web.HTTPUnauthorized(reason='Token missing.')
            elif len(parts) > 2:
                raise web.HTTPUnauthorized(reason='Token contains spaces.')

            try:
                request['auth'] = jwt.decode(parts[1], secret)
            except jwt.JWTError:
                raise web.HTTPUnauthorized(reason='passed token is invalid')
        else:
            request['auth'] = None

        return await handler(request)
    return _auth
