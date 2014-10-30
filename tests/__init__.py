import unittest

import xsnippet
import xsnippet.settings


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        # create a new app instance per test
        self.app = xsnippet.create_app(xsnippet.settings)
        self.client = self.app.test_client()

        # create db schema (we use a new sqlite in-memory schema per test)
        with self.app.app_context():
            xsnippet.db.models.db.create_all()
