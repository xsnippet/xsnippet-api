from xsnippet import create_app
from xsnippet.db import models


class ProductionSettings:
    DEBUG = False
    SQLALCHEMY_ECHO = False


class DebugSettings:
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


if __name__ == "__main__":
    app = create_app(DebugSettings)

    # TODO: use alembic for this
    with app.app_context():
        models.db.create_all()

    app.run()
else:
    app = create_app(ProductionSettings)
