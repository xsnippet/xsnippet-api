"""
    xsnippet.api.conf
    -----------------

    The module provides a function that gathers application settings
    from various sources, combines them and returns them at once.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import os
import configparser

import decouple


def get_conf(envvar=None):
    """Return one settings instance combines from different sources.

    The idea that lies behind that function is to gather config settings
    from different sources, including dynamic once pointed by passed
    environment variable (usually production overrides).

    :param envvar: an environment variable that points to additional config
    :type envvar: str

    :return: a configuration dictionary
    :rtype: :class:`dict`
    """
    # TODO: Drop INI support and use configuration via environment vars only.

    # Due to limitations of INI standard, there's no way to have an option
    # which value is a list. Fortunately, since Python 3.5 we can provide
    # so called converters: an additional functions to convert desired
    # option to consumable format.
    converters = {
        'list': lambda v: list(filter(None, str.splitlines(v)))
    }

    conf = configparser.ConfigParser(converters=converters)
    conf.read_dict({
        'server': {
            # IP ADDRESS TO LISTEN ON
            #
            # By default, only localhost interface is used for listening.
            # That's why no requests from outer world will be handled. If you
            # want to accept any incoming request on any interface, please
            # change that value to '0.0.0.0'.
            'host': decouple.config('XSNIPPET_SERVER_HOST', default='127.0.0.1'),

            # PORT TO LISTEN ON
            #
            # In production you probably will choose a default HTTP port -
            # '80'.  If you want to pick any random free port, just pass '0'.
            'port': decouple.config('XSNIPPET_SERVER_PORT', default=8000, cast=int),

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
            'access_log_format': decouple.config(
                'XSNIPPET_SERVER_ACCESS_LOG_FORMAT',
                default='%t %a "%r" %s %b %{User-Agent}i" %Tf',
                # ConfigParser supports string interpolation so we need to
                # escape '%' before processing.
                cast=lambda value: value.replace('%', '%%')),
        },

        'database': {
            # DATABASE CONNECTION URI
            #
            # Supported backends: MongoDB only
            'connection': decouple.config(
                'XSNIPPET_DATABASE_CONNECTION_URI', default='mongodb://localhost:27017/xsnippet')
        },

        'snippet': {
            'syntaxes': decouple.config(
                'XSNIPPET_SNIPPET_SYNTAXES',
                default='',
                # Convert comma separated list retrieved from env variable
                # to newline separated list ready to be processed by
                # configparser.
                cast=lambda value: value.replace(',', '\n')),
        },

        'auth': {
            'secret': decouple.config('XSNIPPET_AUTH_SECRET', default=''),
        },
    })

    if envvar is not None and envvar in os.environ:
        conf.read(os.environ[envvar])

    return {
        'SERVER_HOST': conf.get('server', 'host'),
        'SERVER_PORT': conf.getint('server', 'port'),
        'SERVER_ACCESS_LOG_FORMAT': conf.get('server', 'access_log_format'),
        'DATABASE_CONNECTION_URI': conf.get('database', 'connection'),
        'SNIPPET_SYNTAXES': conf.getlist('snippet', 'syntaxes'),
        'AUTH_SECRET': conf.get('auth', 'secret'),
    }
