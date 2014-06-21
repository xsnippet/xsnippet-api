from flask import Flask

import xsnippet.db.models


def create_app(conf):
    app = Flask(__name__)

    app.config.from_object(conf)
    app.config.from_envvar('XSNIPPET_SETTINGS', silent=True)

    xsnippet.db.models.db.init_app(app)

    return app
