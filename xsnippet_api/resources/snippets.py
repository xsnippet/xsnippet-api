"""
    xsnippet_api.resources.snippets
    -------------------------------

    The module implements snippets resource that provides CRUD interface
    for code snippets.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import cerberus

from .misc import cerberus_errors_to_str, try_int
from .. import exceptions, resource, services
from ..application import endpoint


class InvalidId(Exception):
    pass


def _get_id(resource):
    v = cerberus.Validator({
        'id': {'type': 'integer', 'min': 1, 'coerce': try_int},
    })

    if not v.validate(dict(resource.request.match_info)):
        raise InvalidId('%s.' % cerberus_errors_to_str(v.errors))

    return int(resource.request.match_info['id'])


async def _write(resource, service_fn, *, status):
    v = cerberus.Validator({
        'id': {'type': 'integer', 'readonly': True},
        'title': {'type': 'string'},
        'content': {'type': 'string', 'required': True},
        'syntax': {'type': 'string'},
        'tags': {'type': 'list',
                 'schema': {'type': 'string', 'regex': '[\w_-]+'}},
        'is_public': {'type': 'boolean'},
        'author_id': {'type': 'integer', 'readonly': True},
        'created_at': {'type': 'datetime', 'readonly': True},
        'updated_at': {'type': 'datetime', 'readonly': True},
    })

    snippet = await resource.read_request()
    conf = resource.request.app['conf']
    syntaxes = conf.getlist('snippet', 'syntaxes', fallback=None)

    # If 'snippet:syntaxes' option is not empty, we need to ensure that
    # only specified syntaxes are allowed.
    if syntaxes:
        v.schema['syntax']['allowed'] = syntaxes

    # In case of PATCH required attributes must become optional, since
    # the operation updates the entity partially and we assume all
    # constraints are satisfied in the database.
    is_patch = resource.request.method.lower() == 'patch'

    if not v.validate(snippet, update=is_patch):
        error = cerberus_errors_to_str(v.errors)
        return resource.make_response({'message': '%s.' % error}, status=400)

    try:
        written = await service_fn(snippet)

    except InvalidId as exc:
        return resource.make_response({'message': str(exc)}, status=400)
    except exceptions.SnippetNotFound as exc:
        return resource.make_response({'message': str(exc)}, status=404)

    return resource.make_response(written, status=status)


async def _read(resource, service_fn, *, status):
    try:
        read = await service_fn(_get_id(resource))

    except InvalidId as exc:
        return resource.make_response({'message': str(exc)}, status=400)
    except exceptions.SnippetNotFound as exc:
        return resource.make_response({'message': str(exc)}, status=404)

    return resource.make_response(read, status=status)


@endpoint('/snippets/{id}', '1.0')
class Snippet(resource.Resource):

    async def get(self):
        return await _read(self, services.Snippet(self.db).get_one, status=200)

    async def delete(self):
        # TODO: only authorized owners can remove their snippets
        return await _read(self, services.Snippet(self.db).delete, status=204)

    async def put(self):
        async def service_fn(snippet):
            snippet['id'] = _get_id(self)
            return await services.Snippet(self.db).replace(snippet)

        # TODO: only authorized owners can update their snippets
        return await _write(self, service_fn, status=200)

    async def patch(self):
        async def service_fn(snippet):
            snippet['id'] = _get_id(self)
            return await services.Snippet(self.db).update(snippet)

        # TODO: only authorized owners can update their snippets
        return await _write(self, service_fn, status=200)


@endpoint('/snippets', '1.0')
class Snippets(resource.Resource):

    async def get(self):
        v = cerberus.Validator({
            'limit': {
                'type': 'integer',
                'min': 1,
                'max': 20,
                'coerce': try_int,
            },
            'marker': {
                'type': 'integer',
                'min': 1,
                'coerce': try_int,
            },
        })

        if not v.validate(dict(self.request.GET)):
            error = '%s.' % cerberus_errors_to_str(v.errors)
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
        return await _write(self, services.Snippet(self.db).create, status=201)
