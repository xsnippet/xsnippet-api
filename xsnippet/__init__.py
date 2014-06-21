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
    app.debug = True

    # TODO: use alembic for this
    with app.app_context():
        xsnippet.db.models.db.create_all()

    app.run()
