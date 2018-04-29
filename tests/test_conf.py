"""Test xsnippet.api.conf module."""

import textwrap

from xsnippet.api.conf import get_conf


def test_get_conf(monkeypatch):
    monkeypatch.setenv('XSNIPPET_SERVER_HOST', '1.2.3.4')
    monkeypatch.setenv('XSNIPPET_SERVER_PORT', 1234)
    monkeypatch.setenv('XSNIPPET_SERVER_ACCESS_LOG_FORMAT', '%x %y')
    monkeypatch.setenv('XSNIPPET_DATABASE_CONNECTION_URI', 'mongodb://42.42.42.42/test')
    monkeypatch.setenv('XSNIPPET_SNIPPET_SYNTAXES', 'foo,bar')
    monkeypatch.setenv('XSNIPPET_AUTH_SECRET', 'x$3cret')

    assert get_conf() == {
        'SERVER_HOST': '1.2.3.4',
        'SERVER_PORT': 1234,
        'SERVER_ACCESS_LOG_FORMAT': '%x %y',
        'DATABASE_CONNECTION_URI': 'mongodb://42.42.42.42/test',
        'SNIPPET_SYNTAXES': ['foo', 'bar'],
        'AUTH_SECRET': 'x$3cret',
    }


def test_get_conf_envvar(tmpdir, monkeypatch):
    tmpdir.join('test.conf').write_text(
        textwrap.dedent('''
            [server]
            host = 1.2.3.4
            port = 1234
            access_log_format = %%x %%y

            [database]
            connection = mongodb://42.42.42.42/test

            [snippet]
            syntaxes = foo
                       bar

            [auth]
            secret = x$3cret
        '''),
        encoding='utf-8')
    monkeypatch.setenv('XSNIPPET_TEST_CONF', tmpdir.join('test.conf').strpath)

    assert get_conf(envvar='XSNIPPET_TEST_CONF') == {
        'SERVER_HOST': '1.2.3.4',
        'SERVER_PORT': 1234,
        'SERVER_ACCESS_LOG_FORMAT': '%x %y',
        'DATABASE_CONNECTION_URI': 'mongodb://42.42.42.42/test',
        'SNIPPET_SYNTAXES': ['foo', 'bar'],
        'AUTH_SECRET': 'x$3cret',
    }


def test_get_conf_defaults():
    assert get_conf() == {
        'SERVER_HOST': '127.0.0.1',
        'SERVER_PORT': 8000,
        'SERVER_ACCESS_LOG_FORMAT': '%t %a "%r" %s %b %{User-Agent}i" %Tf',
        'DATABASE_CONNECTION_URI': 'mongodb://localhost:27017/xsnippet',
        'SNIPPET_SYNTAXES': [],
        'AUTH_SECRET': '',
    }
