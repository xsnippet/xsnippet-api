"""
    xsnippet_api.resources.snippets
    -------------------------------

    The module implements snippets resource that provides CRUD interface
    for code snippets.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import cerberus

from .. import exceptions, resource, services
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


def _try_int(value, base=10):
    try:
        return int(value, base)
    except:
        return value


@endpoint('/snippets/{id}', '1.0')
class Snippet(resource.Resource):

    async def get(self):
        return await self._run(services.Snippet(self.db).get_one, 200)

    async def delete(self):
        # TODO: only authorized owners can remove their snippets
        return await self._run(services.Snippet(self.db).delete, 204)

    async def _run(self, service_fn, status):
        v = cerberus.Validator({
            'id': {'type': 'integer', 'min': 1, 'coerce': _try_int},
        })

        if not v.validate(dict(self.request.match_info)):
            error = '%s.' % _cerberus_errors_to_str(v.errors)
            return self.make_response({'message': error}, status=400)

        try:
            rv = await service_fn(int(self.request.match_info['id']))
        except exceptions.SnippetNotFound as exc:
            return self.make_response({'message': str(exc)}, status=404)

        return self.make_response(rv, status)


@endpoint('/snippets', '1.0')
class Snippets(resource.Resource):

    async def get(self):
        v = cerberus.Validator({
            'limit': {
                'type': 'integer',
                'min': 1,
                'max': 20,
                'coerce': _try_int,
            },
            'marker': {
                'type': 'integer',
                'min': 1,
                'coerce': _try_int,
            },
        })

        if not v.validate(dict(self.request.GET)):
            error = '%s.' % _cerberus_errors_to_str(v.errors)
            return self.make_response({'message': error}, status=400)

        try:
            snippets = await services.Snippet(self.db).get(
                # It's safe to have type cast here since those query parameters
                # are guaranteed to be integer, thanks to validation above.
                limit=int(self.request.GET.get('limit', 0)),
                marker=int(self.request.GET.get('marker', 0)),
            )
        except exceptions.SnippetNotFound as exc:
            return self.make_response({'message': str(exc)}, status=404)

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
            return self.make_response(
                {
                    'message': 'Cannot create a new snippet, passed data are '
                               'incorrect. Found issues: %s.' % error
                }, status=400)

        snippet = await services.Snippet(self.db).create(snippet)
        return self.make_response(snippet, status=201)
