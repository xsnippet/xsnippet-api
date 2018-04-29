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
import aiohttp.web as web
import picobox

from .misc import cerberus_errors_to_str, try_int
from .. import resource, services


def _get_id(resource):
    v = cerberus.Validator({
        'id': {'type': 'integer', 'min': 1, 'coerce': try_int},
    })

    if not v.validate(dict(resource.request.match_info)):
        reason = '%s.' % cerberus_errors_to_str(v.errors)
        raise web.HTTPBadRequest(reason=reason)

    return int(resource.request.match_info['id'])


@picobox.pass_('conf')
async def _write(resource, service_fn, *, status, conf):
    v = cerberus.Validator({
        'id': {'type': 'integer', 'readonly': True},
        'title': {'type': 'string'},
        'content': {'type': 'string', 'required': True, 'empty': False},
        'syntax': {'type': 'string'},
        'tags': {'type': 'list',
                 'schema': {'type': 'string', 'regex': '[\w_-]+'}},
        'created_at': {'type': 'datetime', 'readonly': True},
        'updated_at': {'type': 'datetime', 'readonly': True},
    })

    snippet = await resource.request.get_data()
    syntaxes = conf['SNIPPET_SYNTAXES']

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
        raise web.HTTPBadRequest(reason='%s.' % error)

    written = await service_fn(snippet)
    return written, status


async def _read(resource, service_fn, *, status):
    read = await service_fn(_get_id(resource))
    return read, status


class Snippet(resource.Resource):

    def checkpermissions(fn):
        @functools.wraps(fn)
        @picobox.pass_('conf')
        async def _wrapper(self, conf, *args, **kwargs):
            # So far there's no way to check user's permissions as we don't
            # track users and snippets' owners. However, we do support methods
            # to change the snippet and we need to ensure it's not exposed to
            # public but can be tested. That's why we check for a fake flag in
            # conf object that can be set in tests in order to test existing
            # functionality.
            if not conf.get('_SUDO', False):
                raise web.HTTPForbidden(reason='Not yet. :)')
            return await fn(self, *args, **kwargs)
        return _wrapper

    async def get(self):
        return await _read(self, services.Snippet().get_one, status=200)

    @checkpermissions
    async def delete(self):
        return await _read(self, services.Snippet().delete, status=204)

    @checkpermissions
    async def put(self):
        async def service_fn(snippet):
            snippet['id'] = _get_id(self)
            return await services.Snippet().replace(snippet)

        return await _write(self, service_fn, status=200)

    @checkpermissions
    async def patch(self):
        async def service_fn(snippet):
            snippet['id'] = _get_id(self)
            return await services.Snippet().update(snippet)

        return await _write(self, service_fn, status=200)


def _build_url_from_marker(request, marker=None, limit=None):
    # take into account, that we might be running behind a reverse proxy
    host = request.headers.get('Host', request.url.host).split(':')[0]
    proto = request.headers.get('X-Forwarded-Proto', request.scheme)

    # drop the previous values of limit and marker
    new_query = request.url.query.copy()
    new_query.pop('limit', None)
    new_query.pop('marker', None)

    # and replace them with new ones (if necessary for the given page)
    if limit:
        new_query['limit'] = limit
    if marker:
        new_query['marker'] = marker

    return request.url.with_scheme(proto) \
                      .with_host(host) \
                      .with_query(new_query)


def _build_link_header(request, current_page, previous_page, limit):
    links = []

    # always render a link to the first page
    url = _build_url_from_marker(request, marker=None, limit=limit)
    links.append('<%s>; rel="first"' % url)

    # only render a link, if there more items after the current page
    if len(current_page) > limit:
        marker = current_page[:limit][-1]['id']
        url = _build_url_from_marker(request, marker=marker, limit=limit)

        links.append('<%s>; rel="next"' % url)

    if len(previous_page) >= limit:
        # account for the edge case when there is exactly one full page left -
        # in this case the request for the previous page should be w/o any
        # marker value passed
        if len(previous_page) == limit:
            marker = None
        else:
            marker = previous_page[-1]['id']
        url = _build_url_from_marker(request, marker=marker, limit=limit)

        links.append('<%s>; rel="prev"' % url)

    return ', '.join(links)


class Snippets(resource.Resource):

    @picobox.pass_('conf')
    async def get(self, conf):
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
            },
            'syntax': {
                'type': 'string',
            },
        })

        syntaxes = conf['SNIPPET_SYNTAXES']

        # If 'snippet:syntaxes' option is not empty, we need to ensure that
        # only specified syntaxes are allowed.
        if syntaxes:
            v.schema['syntax']['allowed'] = syntaxes

        if not v.validate(dict(self.request.query)):
            error = '%s.' % cerberus_errors_to_str(v.errors)
            raise web.HTTPBadRequest(reason=error)

        # It's safe to have type cast here since those query parameters
        # are guaranteed to be integer, thanks to validation above.
        limit = int(self.request.query.get('limit', 20))
        marker = int(self.request.query.get('marker', 0))
        title = self.request.query.get('title')
        tag = self.request.query.get('tag')
        syntax = self.request.query.get('syntax')

        # actual snippets to be returned
        current_page = await services.Snippet().get(
            title=title, tag=tag, syntax=syntax,
            # read one more to know if there is next page
            limit=limit + 1,
            marker=marker,
        )

        # only needed to render a link to the previous page
        if marker:
            previous_page = await services.Snippet().get(
                title=title, tag=tag, syntax=syntax,
                # read one more to know if there is prev page
                limit=limit + 1,
                marker=marker,
                direction='backward'
            )
        else:
            # we are at the very beginning of the list - no prev page
            previous_page = []

        return (
            # return no more than $limit snippets (if we read $limit + 1)
            current_page[:limit],
            200,
            {
                'Link': _build_link_header(
                    self.request,
                    current_page, previous_page,
                    limit=limit,
                )
            },
        )

    async def post(self):
        return await _write(self, services.Snippet().create, status=201)
