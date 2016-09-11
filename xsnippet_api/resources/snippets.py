"""
    xsnippet_api.resources.snippets
    -------------------------------

    The module implements snippets resource that provides CRUD interface
    for code snippets.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import aiohttp.web as web
import cerberus

from .. import resource, services
from ..application import endpoint


_schema = {
    'id': {'type': 'integer', 'readonly': True},
    'title': {'type': 'string'},
    'content': {'type': 'string', 'required': True},
    'syntax': {'type': 'string'},
    'tags': {'type': 'list', 'schema': {'type': 'string', 'regex': '[\w_-]+'}},
    'is_public': {'type': 'boolean'},
    'author_id': {'type': 'integer', 'readonly': True},
    'created_at': {'type': 'datetime', 'readonly': True},
    'updated_at': {'type': 'datetime', 'readonly': True},
}


def _cerberus_errors_to_str(errors):
    parts = []
    for name, reasons in errors.items():
        for reason in reasons:
            parts.append('`%s` - %s' % (name, reason))
    return ', '.join(parts)


@endpoint('/snippets/{id}', '1.0')
class Snippet(resource.Resource):

    async def get(self):
        try:
            _id = int(self.request.match_info['id'])
        except (ValueError, TypeError):
            raise web.HTTPBadRequest()

        snippet = await services.Snippet(self.db).get_one(_id)
        return self.make_response(snippet)

    async def delete(self):
        try:
            _id = int(self.request.match_info['id'])
        except (ValueError, TypeError):
            raise web.HTTPBadRequest()

        # TODO: only allow authorized users to delete their snippets

        await services.Snippet(self.db).delete(_id)
        return self.make_response('', status=204)  # No Content


@endpoint('/snippets', '1.0')
class Snippets(resource.Resource):

    async def get(self):
        try:
            # TODO: get value from conf
            marker = int(self.request.GET.get('marker', 0))
            limit = min(int(self.request.GET.get('limit', 20)), 20)
        except (ValueError, TypeError):
            raise web.HTTPBadRequest()

        snippets = await services.Snippet(self.db).get(limit=limit,
                                                       marker=marker)
        return self.make_response(snippets, status=200)

    async def post(self):
        snippet = await self.read_request()

        conf = self.request.app['conf']
        syntaxes = conf.getlist('snippet', 'syntaxes', fallback=None)
        v = cerberus.Validator(_schema)

        if not v.validate(snippet):
            error = _cerberus_errors_to_str(v.errors)
        elif syntaxes and snippet.get('syntax') not in syntaxes:
            error = '`syntax` - invalid value'
        else:
            error = None

        if error:
            return self.make_response({
                'message': (
                    'Cannot create a new snippet, passed data are incorrect. '
                    'Found issues: %s.' % error
                )
            }, status=400)

        snippet = await services.Snippet(self.db).create(snippet)
        return self.make_response(snippet, status=201)
