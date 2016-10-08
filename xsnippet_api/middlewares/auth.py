"""
    xsnippet_api.middlewares.auth
    -------------------------------

    The module implements auth middleware that performs authentication
    of user requests.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import aiohttp.web as web
import jose.jwt as jwt


async def auth(conf, app, next_handler):
    """Authentication middleware.

    Performs user authentication by validating tokens passed in Authorization
    header. Tokens are expected to be in JSON Web Token (RFC 7519) format.

    On success the request object is modified to store an additional key 'auth'
    which points to the parsed token value.

    On failure 401 Unauthorized error is raised.
    """

    try:
        secret = conf['secret']
    except KeyError:
        raise ValueError("Option 'secret' is required to be set when "
                         "auth middleware is enabled")

    async def auth_handler(request):
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

        return await next_handler(request)

    return auth_handler
