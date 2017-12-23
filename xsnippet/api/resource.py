"""
    xsnippet.api.resource
    ---------------------

    The module provides a base class of RESTful API resources. It's not
    exposed via :ref:`xsnippet.api.resources` package, and is intended
    for internal usage only.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import json
import datetime
import fnmatch
import functools

from aiohttp import web, hdrs
from werkzeug import http


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
    """Resource wrapper around :class:`aiohttp.web.View`.

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

    def __init__(self, *args, **kwargs):
        super(Resource, self).__init__(*args, **kwargs)

        #: an application database alias to make code a bit readable
        self.db = self.request.app['db']

    def make_response(self, data, status=200):
        """Return an HTTP response object.

        The method serializes given data according to 'Accept' HTTP header,
        and wraps result into :class:`aiohttp.web.Response`.

        :param data: a data to be responded to client
        :type data: a serializable python object

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
                        content_type=supported_accept,
                        text=encode(data),
                    )

        raise web.HTTPNotAcceptable()

    async def read_request(self):
        """Return parsed request data.

        The method reads request's payload and tries to deserialize it
        according to 'Content-Type' header.

        :return: a deserialized content
        :rtype: python object

        :raise: :class:`aiohttp.web.HTTPUnsupportedMediaType`
        """
        if self.request.content_type in self._decoders:
            decode = self._decoders[self.request.content_type]
            return decode(await self.request.text())

        raise web.HTTPUnsupportedMediaType()
