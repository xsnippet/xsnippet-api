"""
    xsnippet.api.application
    ------------------------

    Provides a factory function to create an application instance,
    ready to be served by :function:`aiohttp.web.run_app`.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import functools

import aiohttp.web
import picobox

from . import database, routes, middlewares


@picobox.pass_('conf')
@picobox.pass_('database', as_='db')
def create_app(conf, db):
    """Create and return a web application instance.

    The whole point of that function is to provide a way to create
    a full-featured application instance with database sesstion,
    routes and so on.

    :param conf: a settings to be used to create an application instance
    :type conf: :class:`dict`

    :return: an application instance
    :rtype: :class:`aiohttp.web.Application`
    """

    app = aiohttp.web.Application(
        middlewares=[
            middlewares.auth.auth(conf),
        ])
    app.router.add_routes(routes.v1)
    app.on_startup.append(functools.partial(database.setup, db=db))

    return app
