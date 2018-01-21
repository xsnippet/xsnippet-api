"""
    xsnippet.api.resource
    ---------------------

    The module provides a base class of RESTful API resources. It's not
    exposed via :ref:`xsnippet.api.resources` package, and is intended
    for internal usage only.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import asyncio
import json
import datetime
import fnmatch
import functools

from aiohttp import web, hdrs
from werkzeug import http

from . import exceptions


class _JSONEncoder(json.JSONEncoder):
    """Advanced JSON encoder for extra data types.

    Extra support of the following data types:

      - :class:`datetime.datetime` -- encoded into ISO-8601 formatted string
      - :class:`datetime.date` -- encoded into ISO-8601 formatted string
    """

    def default(self, instance):
        if isinstance(instance, (datetime.datetime, datetime.date)):
            return instance.isoformat()
        return super().default(instance)


class Resource(web.View):
    """Class-based view to represent RESTful resource.

    The class provides basic facilities for building RESTful API, such as
    encoding responses according to ``Accept`` and decoding requests
    according to ``Content-Type`` HTTP headers.

    Yet it provides a quick access to application database.
    """

    _encoders = {
        'application/json': functools.partial(json.dumps, cls=_JSONEncoder),
    }

    _decoders = {
        'application/json': json.loads,
    }

    @asyncio.coroutine
    def __iter__(self):
        # So far (Jan 5, 2018) aiohttp doesn't support custom request classes,
        # but we would like to provide a better user experience for consumers
        # of this middleware. Hence, we monkey patch the instance and add a new
        # async method that would de-serialize income payload according to HTTP
        # content negotiation rules.
        setattr(self.request.__class__, 'get_data', self._get_data())

        try:
            response = yield from super(Resource, self).__iter__()

        except exceptions.SnippetNotFound as exc:
            error = {'message': str(exc)}
            return self._make_response(error, None, 404)

        except web.HTTPError as exc:
            error = {'message': str(exc)}
            return self._make_response(error, None, exc.status_code)

        status_code = 200
        headers = None

        if isinstance(response, tuple):
            response, status_code, *rest = response
            if rest:
                headers = rest[0]

        return self._make_response(response, headers, status_code)

    def _make_response(self, data, headers=None, status=200):
        """Return an HTTP response object.

        The method serializes given data according to 'Accept' HTTP header,
        and wraps result into :class:`aiohttp.web.Response`.

        :param data: a data to be responded to client
        :type data: a serializable python object

        :param headers: response headers to be returned to client
        :type headers: dict

        :param status: an HTTP status code
        :type status: int

        :return: a response object encoded according to ``Accept`` HTTP header
        :rtype: :class:`aiohttp.web.Response`

        :raise: :class:`aiohttp.web.HTTPNotAcceptable`
        """
        # By an HTTP standard the 'Accept' header might have multiple
        # media ranges (i.e. types) specified with priority. Moreover,
        # we also may have several 'Accept' headers in one HTTP request.
        #
        # This is going to parse them and prioritize, so we respond
        # with most preferable content type.
        #
        # No header means any type.
        accepts = http.parse_accept_header(

            # combine few headers into one in order to simplify parsing,
            # or use any type pattern if no headers are passed
            ','.join(self.request.headers.getall(hdrs.ACCEPT, ['*/*']))
        )

        for accept, _ in accepts:
            for supported_accept, encode in self._encoders.items():

                # since 'Accept' may contain glob patterns (e.g. */*) we
                # can't use dict lookup and should search for suitable
                # encoder manually
                if fnmatch.fnmatch(supported_accept, accept):
                    return web.Response(
                        status=status,
                        headers=headers,
                        content_type=supported_accept,
                        text=encode(data),
                    )

        raise web.HTTPNotAcceptable()

    def _get_data(self):
        decoders = self._decoders

        async def impl(self):
            if self.content_type in decoders:
                decode = decoders[self.content_type]
                return decode(await self.text())

            raise web.HTTPUnsupportedMediaType()
        return impl
