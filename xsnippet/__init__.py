# coding: utf-8
"""
    xsnippet
    ~~~~~~~~

    XSnippet is a simple Web-service for sharing code snippets on the Internet.
    It's written in Python using Flask, SQLAlchemy and PostgreSQL.

    :copyright: (c) 2014, XSnippet Team
    :license: BSD, see LICENSE for details
"""
from flask import Flask

import xsnippet.db.models
import xsnippet.views.v1


def create_app(conf):
    app = Flask(__name__)

    app.config.from_object(conf)
    app.config.from_envvar('XSNIPPET_SETTINGS', silent=True)

    app.register_blueprint(xsnippet.views.v1.api, url_prefix='/api/v1')

    xsnippet.db.models.db.init_app(app)

    return app


if __name__ == "__main__":
    app = create_app('xsnippet.settings')

    # TODO: use alembic for this
    with app.app_context():
        xsnippet.db.models.db.create_all()

    app.run()
