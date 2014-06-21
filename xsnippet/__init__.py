from flask import Flask

import xsnippet.db.models
import xsnippet.views.v1


def create_app(conf):
    app = Flask(__name__)

    app.config.from_object(conf)
    app.config.from_envvar('XSNIPPET_SETTINGS', silent=True)

    app.register_blueprint(xsnippet.views.v1.api)

    xsnippet.db.models.db.init_app(app)

    return app
