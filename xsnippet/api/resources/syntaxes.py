"""
    xsnippet.api.resources.syntaxes
    -------------------------------

    The module implements the resource, that allows to retrieve
    the list of supported snippet syntaxes.

    :copyright: (c) 2017 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import picobox

from .. import resource


class Syntaxes(resource.Resource):
    @picobox.pass_("conf")
    async def get(self, conf):
        return conf["SNIPPET_SYNTAXES"]
