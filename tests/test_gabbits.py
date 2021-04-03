import base64
import json
import math
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
import jwt
import sqlalchemy

from cryptography.hazmat.primitives.asymmetric import rsa
from gabbi.driver import test_pytest


XSNIPPET_API_HOST = "127.0.0.1"
XSNIPPET_API_PORT = 8000


def _random_name(length=8):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


def _base64urlUint(num):
    """base64url encoding of the value's unsigned big-endian representation."""

    # RFC 7518: "The octet sequence MUST utilize the minimum number of octets needed to represent the value"
    length = math.ceil(math.log(num, 2) / 8)

    return base64.urlsafe_b64encode(num.to_bytes(length, byteorder="big")).decode()


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


class XSnippetApiWithCustomAuthProvider(XSnippetApi):
    """Start live server of XSnippet API with a custom auth provider.

    This allows to run the tests w/o access to Auth0 and verify some additional
    negative scenarios like using of valid signatures generated by an unexpected
    third-party.

    The test fixture acts as an auth provider:

    * it generates an RSA keypair for signing and validating tokens
    * the RSA private key is used to create a few tokens for various test cases
    * the RSA public key is made available to XSnippet API via a temporary file
    """

    JWT_AUDIENCE = "xsnippet-api-tests-aud"
    JWT_ISSUER = "xsnippet-api-tests-iss"
    JWT_KEY_ID = "test-key"
    JWT_KEY_TYPE = "RSA"
    JWT_ALGORITHM = "RS256"

    def start_fixture(self):
        private_key, public_key = self._generate_rsa_keypair()

        self.jwks = tempfile.NamedTemporaryFile('wt')
        self.jwks.write(self._generate_jwks_content(public_key))
        self.jwks.flush()

        self.environ.update({
            "ROCKET_JWT_AUDIENCE": self.JWT_AUDIENCE,
            "ROCKET_JWT_ISSUER": self.JWT_ISSUER,
            "ROCKET_JWT_JWKS_URI": "file://{}".format(self.jwks.name),
        })

        # this is ugly, but apparentely there is no other way to generate some
        # data in a Gabbi test fixture, and then use it in the YAML scenarios
        self.tokens = self._generate_tokens(private_key)
        os.environ.update(self.tokens)

        super().start_fixture()

    def stop_fixture(self):
        try:
            super().stop_fixture()
        finally:
            # clean up the tokens, so that they do not accidentally linger and
            # get picked up by other test cases
            for key in self.tokens:
                os.environ.pop(key, None)

            self.jwks.close()
            self.jwks = None

    def _generate_rsa_keypair(self, public_exponent=65537, key_size=2048):
        private_key = rsa.generate_private_key(public_exponent, key_size)
        public_key = private_key.public_key()

        return (private_key, public_key)

    def _generate_tokens(self, private_key):
        def generate(subject,
                     audience=self.JWT_AUDIENCE,
                     issuer=self.JWT_ISSUER,
                     permissions=(),
                     expires_in=24 * 60 * 60,
                     key_id=self.JWT_KEY_ID,
                     algorithm=self.JWT_ALGORITHM):
            claims = {
                "sub": subject,
                "aud": audience,
                "iss": issuer,
                "exp": int(time.time()) + expires_in,
                "permissions": permissions,
            }

            return jwt.encode(claims, private_key, algorithm,
                              headers={"kid": key_id})

        return {
            "TOKEN_VALID": generate("user"),
            "TOKEN_ADMIN": generate("admin", permissions=("admin", )),
            "TOKEN_EXPIRED": generate("user", expires_in=-3600),
            "TOKEN_UNKNOWN_KEY": generate("user", key_id="spam"),
            "TOKEN_UNSUPPORTED_ALGORITHM": generate("user", algorithm="PS256"),
            "TOKEN_INVALID_AUDIENCE": generate("user", audience="spam"),
            "TOKEN_INVALID_ISSUER": generate("user", issuer="eggs"),
        }

    def _generate_jwks_content(self, public_key):
        params = public_key.public_numbers()

        return json.dumps({
            "keys": [
                {
                    "alg": self.JWT_ALGORITHM,
                    "kty": self.JWT_KEY_TYPE,
                    "use": "sig",
                    "n": _base64urlUint(params.n),
                    "e": _base64urlUint(params.e),
                    "kid": self.JWT_KEY_ID,
                    # these two fields are currently ignored by XSnippet API,
                    # so we just need to make sure they have the expected types
                    "x5t": "",
                    "x5c": [],
                }
            ],
        })


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
