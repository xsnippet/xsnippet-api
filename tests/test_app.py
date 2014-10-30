import xsnippet.db.models

from . import BaseTestCase


class AppTestCase(BaseTestCase):
    def test_db_schema_is_created(self):
        with self.app.app_context():
            eng = xsnippet.db.models.db.engine
            self.assertNotEqual(0, eng.table_names())
