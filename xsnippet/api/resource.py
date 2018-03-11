"""
    xsnippet.api.resource
    ---------------------

    The module provides a base class of RESTful API resources. It's not
    exposed via :ref:`xsnippet.api.resources` package, and is intended
    for internal usage only.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import cgi
import json
import datetime
import functools

from aiohttp import web, hdrs
import werkzeug

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

    def __await__(self):
        return self._poor_asyncio_api().__await__()

    async def _poor_asyncio_api(self):
        # So far (Jan 5, 2018) aiohttp doesn't support custom request classes,
        # but we would like to provide a better user experience for consumers
        # of this middleware. Hence, we monkey patch the instance and add a new
        # async method that would de-serialize income payload according to HTTP
        # content negotiation rules.
        setattr(self.request.__class__, 'get_data', self._get_data())

        try:
            # TODO: do not access internal method of parent class
            response = await super(Resource, self)._iter()

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
        mimeaccept = werkzeug.parse_accept_header(
            # According to HTTP standard, 'Accept' header may show up multiple
            # times in the request. So let's join them before passing to parser
            # so we call parser only once.
            ','.join(self.request.headers.getall(hdrs.ACCEPT, ['*/*'])),

            # A handful wrapper to choose a best match with one method.
            werkzeug.MIMEAccept,
        )

        # According to HTTP standard, 'Accept' header may have multiple media
        # ranges (i.e. MIME types), each specified with a priority. So choose
        # one that matches best for further usage.
        accept = mimeaccept.best_match(self._encoders)

        if accept in self._encoders:
            return web.Response(
                status=status,
                headers=headers,
                content_type=accept,
                text=self._encoders[accept](data),
            )

        raise web.HTTPNotAcceptable()

    def _get_data(self):
        decoders = self._decoders

        async def impl(self):
            # We cannot use 'self.content_type' here because aiohttp follows
            # RFC 2616, and if nothing is passed set content type to
            # application/octet-stream. So check raw headers instead and
            # fallback for first available decoders if not found. We also need
            # to parse headers, as some mime types may contain parameters and
            # we need to strip them out.
            content_type, _ = cgi.parse_header(
                self.headers.get(hdrs.CONTENT_TYPE, next(iter(decoders))))

            if content_type in decoders:
                decode = decoders[content_type]
                return decode(await self.text())

            raise web.HTTPUnsupportedMediaType()
        return impl
