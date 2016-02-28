"""
    xsnippet_api.conf
    -----------------

    The module provides a function that gathers application settings
    from various sources, combines them and returns them at once.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import os
import configparser


def get_conf(paths, envvar=None):
    """Return one settings instance combines from different sources.

    The idea that lies behind that function is to gather config settings
    from different sources, including dynamic once pointed by passed
    environment variable (usually production overrides).

    :param paths: a list of paths to configuration files
    :type paths: [str]

    :param envvar: an environment variable that points to additional config
    :type envvar: str

    :return: a configuration instance
    :rtype: :class:`configparser.ConfigParser`
    """
    conf = configparser.ConfigParser()
    conf.read(paths)

    if envvar is not None and envvar in os.environ:
        conf.read(os.environ[envvar])

    return conf