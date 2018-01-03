"""
    xsnippet.api.resources.snippets
    -------------------------------

    The module implements snippets resource that provides CRUD interface
    for code snippets.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import functools

import cerberus

from .misc import cerberus_errors_to_str, try_int
from .. import exceptions, resource, services


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


class Snippet(resource.Resource):

    def checkpermissions(fn):
        @functools.wraps(fn)
        async def _wrapper(self, *args, **kwargs):
            # So far there's no way to check user's permissions as we don't
            # track users and snippets' owners. However, we do support methods
            # to change the snippet and we need to ensure it's not exposed to
            # public but can be tested. That's why we check for a fake flag in
            # conf object that can be set in tests in order to test existing
            # functionality.
            conf = self.request.app['conf']
            if not conf.getboolean('test', 'sudo', fallback=False):
                return self.make_response(
                    {
                        'message': 'Not yet. :)'
                    },
                    status=403)
            return await fn(self, *args, **kwargs)
        return _wrapper

    async def get(self):
        return await _read(self, services.Snippet(self.db).get_one, status=200)

    @checkpermissions
    async def delete(self):
        return await _read(self, services.Snippet(self.db).delete, status=204)

    @checkpermissions
    async def put(self):
        async def service_fn(snippet):
            snippet['id'] = _get_id(self)
            return await services.Snippet(self.db).replace(snippet)

        return await _write(self, service_fn, status=200)

    @checkpermissions
    async def patch(self):
        async def service_fn(snippet):
            snippet['id'] = _get_id(self)
            return await services.Snippet(self.db).update(snippet)

        return await _write(self, service_fn, status=200)


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
            'title': {
                'type': 'string',
                'empty': False,
            },
            'tag': {
                'type': 'string',
                'regex': '[\w_-]+',
            }
        })

        if not v.validate(dict(self.request.GET)):
            error = '%s.' % cerberus_errors_to_str(v.errors)
            return self.make_response({'message': error}, status=400)

        try:
            snippets = await services.Snippet(self.db).get(
                title=self.request.GET.get('title'),
                tag=self.request.GET.get('tag'),
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
