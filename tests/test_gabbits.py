import json
import os
import random
import socket
import subprocess
import sys
import time

import gabbi.driver
import gabbi.fixture

from gabbi.driver import test_pytest


XSNIPPET_API_HOST = "127.0.0.1"
XSNIPPET_API_PORT = 8000
XSNIPPET_API_DATABASE_URL = os.getenv("ROCKET_DATABASE_URL")


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
            "ROCKET_DATABASE_URL": XSNIPPET_API_DATABASE_URL,
        }

        if self._syntaxes:
            # ROCKET_SYNTAXES expects a TOML array as input. Since TOML library
            # for Python does not provide public means to serialize just a
            # standalone array, we're relying on the fact that a JSON array of
            # strings is fully compatible with a TOML array.
            self.environ["ROCKET_SYNTAXES"] = json.dumps(self._syntaxes)

        self.process = None

    def start_fixture(self):
        """Start the live server."""

        environ = os.environ.copy()
        environ.update(self.environ)

        self.process = subprocess.Popen(self._launch_command, env=environ)
        _wait_for_socket(XSNIPPET_API_HOST, XSNIPPET_API_PORT, self._launch_timeout)

    def stop_fixture(self):
        """Stop the live server."""

        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=self._shutdown_timeout)
            except TimeoutError:
                self.process.kill()
            finally:
                self.process = None


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
