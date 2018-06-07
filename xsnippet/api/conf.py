"""
    xsnippet.api.conf
    -----------------

    The module provides a function that gathers application settings
    from various sources, combines them and returns them at once.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import decouple


def get_conf():
    """Return a settings instance based on configuration via env variables.

    :return: a configuration dictionary
    :rtype: :class:`dict`
    """

    return {
        # IP ADDRESS TO LISTEN ON
        #
        # By default, only localhost interface is used for listening.
        # That's why no requests from outer world will be handled. If you
        # want to accept any incoming request on any interface, please
        # change that value to '0.0.0.0'.
        'SERVER_HOST': decouple.config(
            'XSNIPPET_SERVER_HOST',
            default='127.0.0.1'
        ),
        # PORT TO LISTEN ON
        #
        # In production you probably will choose a default HTTP port -
        # '80'.  If you want to pick any random free port, just pass '0'.
        'SERVER_PORT': decouple.config(
            'XSNIPPET_SERVER_PORT',
            default=8000,
            cast=int
        ),
        # ACCESS LOG FORMAT
        #
        # Note, that you have to use double % signs for escaping to work.
        #
        # %t  - datetime of the request
        # %a  - remote address
        # %r  - request status line
        # %s  - response status code
        # %b  - response size (bytes)
        # %Tf - request time (seconds)
        #
        # When deployed behind a reverse proxy, consider using the value of
        # headers like X-Real-IP or X-Forwarded-For instead of %a
        'SERVER_ACCESS_LOG_FORMAT': decouple.config(
            'XSNIPPET_SERVER_ACCESS_LOG_FORMAT',
            default='%t %a "%r" %s %b %{User-Agent}i" %Tf',
        ),
        # DATABASE CONNECTION URI
        #
        # Supported backends: MongoDB only
        'DATABASE_CONNECTION_URI': decouple.config(
            'XSNIPPET_DATABASE_CONNECTION_URI',
            default='mongodb://localhost:27017/xsnippet'
        ),
        'SNIPPET_SYNTAXES': decouple.config(
            'XSNIPPET_SNIPPET_SYNTAXES',
            default='',
            # parse a comma separated list retrieved from env variable
            cast=lambda value: [v for v in value.split(',') if v]
        ),
        'AUTH_SECRET': decouple.config(
            'XSNIPPET_AUTH_SECRET',
            default=''
        ),
    }
