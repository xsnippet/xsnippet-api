import json
import os
import random
import socket
import string
import subprocess
import sys
import tempfile
import time

import alembic.config
import gabbi.driver
import gabbi.fixture
import sqlalchemy

from gabbi.driver import test_pytest


XSNIPPET_API_HOST = "127.0.0.1"
XSNIPPET_API_PORT = 8000


def _random_name(length=8):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


class XSnippetApi(gabbi.fixture.GabbiFixture):
    """Start live server of XSnippet API."""

    _launch_command = ["cargo", "run"]
    _launch_timeout = 5.0
    _shutdown_timeout = 5.0
    _syntaxes = ["python", "rust", "clojure", "json", "lua"]

    def __init__(self):
        self.environ = {
            "ROCKET_ADDRESS": XSNIPPET_API_HOST,
            "ROCKET_PORT": str(XSNIPPET_API_PORT),
            "ROCKET_LOG": "critical",
            "ROCKET_TRACING": "debug",
        }

        if self._syntaxes:
            # ROCKET_SYNTAXES expects a TOML array as input. Since TOML library
            # for Python does not provide public means to serialize just a
            # standalone array, we're relying on the fact that a JSON array of
            # strings is fully compatible with a TOML array.
            self.environ["ROCKET_SYNTAXES"] = json.dumps(self._syntaxes)

        self.process = None

    def setup_db(self):
        """Create a temporary database and apply schema migrations."""

        # admin connection that allows creation of new databases
        self.management_db = sqlalchemy.create_engine(
            os.getenv("ROCKET_DATABASE_URL"),
            execution_options={
                # required for CREATE/DROP DATABASE which are not transactional
                "isolation_level": "AUTOCOMMIT",
            },
        )

        # create a temporary database with a random name
        self.test_db_url = self.management_db.url.set(database=_random_name())

        with self.management_db.connect() as conn:
            conn.execute(
                "CREATE DATABASE {database} OWNER {username};".format(
                    **self.test_db_url.translate_connect_args()))

        # apply schema migrations to the temporary database. Both
        # Alembic and XSnippet API expect the connection string to be
        # passed via the ROCKET_DATABASE_URL environment variable, so
        # we update the variable to point to the temporary database for
        # the duration of the test
        os.environ["ROCKET_DATABASE_URL"] = str(self.test_db_url)
        alembic.config.main(["upgrade", "head"])

    def teardown_db(self):
        """Clean up the temporary database."""

        with self.management_db.connect() as conn:
            conn.execute("DROP DATABASE IF EXISTS {};".format(self.test_db_url.database))

        # restore the original value of ROCKET_DATABASE_URL, so that
        # it can be used by the fixture to create new databases again
        os.environ["ROCKET_DATABASE_URL"] = str(self.management_db.url)

    def start_fixture(self):
        """Start the live server."""

        self.setup_db()

        environ = os.environ.copy()
        environ.update(self.environ)

        # capture stdout/stderr of xsnippet-api process to a temporary file.
        # Alternatively, we could either connect the child process to our
        # file descriptors (in which case, log messages from both processes
        # would interleave), or connect them to a pipe (this is also not great,
        # because the child process can easily fill up the pipe buffer if we do
        # not regularly read from it in a separate thread).
        self.application_log = tempfile.TemporaryFile()
        self.process = subprocess.Popen(self._launch_command, env=environ,
                                        stdout=self.application_log,
                                        stderr=subprocess.STDOUT)
        _wait_for_socket(XSNIPPET_API_HOST, XSNIPPET_API_PORT, self._launch_timeout)

    def stop_fixture(self):
        """Stop the live server."""

        try:
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=self._shutdown_timeout)
                except TimeoutError:
                    self.process.kill()
                finally:
                    self.application_log.seek(0)
                    print('xsnippet-api log:')
                    print(self.application_log.read().decode())
                    self.application_log.close()

                    self.process = None
        finally:
            self.teardown_db()


class XSnippetApiWithShuffledSyntaxes(XSnippetApi):
    """Start live server of XSnippet API with a shuffled list of syntaxes."""

    @property
    def _syntaxes(self):
        syntaxes = super()._syntaxes.copy()
        random.shuffle(syntaxes)
        return syntaxes


class XSnippetApiWithNoSyntaxes(XSnippetApi):
    """Start live server of XSnippet API with no syntaxes configured."""

    _syntaxes = None


def _wait_for_socket(host, port, timeout):
    """Wait for socket to start accepting connections."""

    start_time = time.monotonic()

    while True:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                break
        except Exception:
            if time.monotonic() - start_time >= timeout:
                raise TimeoutError(
                    f"Waited to long for the port {port} on host {host} to "
                    f"start accepting connections."
                )
            time.sleep(0.1)


def pytest_generate_tests(metafunc):
    gabbi.driver.py_test_generator(
        os.path.join(os.path.dirname(__file__), "gabbits"),
        host=XSNIPPET_API_HOST,
        port=XSNIPPET_API_PORT,
        fixture_module=sys.modules[__name__],
        metafunc=metafunc,
    )
