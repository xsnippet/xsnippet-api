"""
    tests.resources.test_syntaxes
    -----------------------------

    Tests Syntaxes resource.

    :copyright: (c) 2017 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import pytest


async def test_get_syntaxes_default_conf(testapp):
    resp = await testapp.get(
        "/v1/syntaxes", headers={"Accept": "application/json"}
    )
    assert resp.status == 200
    assert await resp.json() == []


@pytest.mark.parametrize("syntaxes", [[], ["clojure", "python"]])
async def test_get_syntaxes_overriden_conf(testapp, testconf, syntaxes):
    testconf["SNIPPET_SYNTAXES"] = syntaxes

    resp = await testapp.get(
        "/v1/syntaxes", headers={"Accept": "application/json"}
    )
    assert resp.status == 200
    assert await resp.json() == syntaxes


async def test_get_syntaxes_overriden_conf_no_syntaxes(testapp, testconf):
    testconf["SNIPPET_SYNTAXES"] = []

    resp = await testapp.get(
        "/v1/syntaxes", headers={"Accept": "application/json"}
    )
    assert resp.status == 200
    assert await resp.json() == []


@pytest.mark.parametrize("method", ["delete", "post", "put"])
async def test_get_syntaxes_unsupported_method(testapp, method):
    func = getattr(testapp, method)

    resp = await func("/v1/syntaxes", headers={"Accept": "application/json"})
    assert resp.status == 405
    assert "Method Not Allowed" in await resp.text()


async def test_get_syntaxes_unsupported_accept_type(testapp):
    resp = await testapp.get(
        "/v1/syntaxes", headers={"Accept": "application/xml"}
    )
    assert resp.status == 406
    assert "Not Acceptable" in await resp.text()
