# coding: utf-8
import urllib

from basehandler import BaseHandler
from model import Snippet


class ListSnippet(BaseHandler):
    '''
        Return the list of snippets that meet the given requirements (author, language, etc)

        Processes GET and POST requests.

        Requirements are specified in url path, i.e. a query:
            GET /author/Jimmy%20Black
        will return the list of snippets whose author is Jimmy Black

        List of snippet properties consits of:
            language
            author
            tags
            title
    '''

    FETCH_LIMIT = 20

    def get(self, key, value, limit=FETCH_LIMIT):
        self.post(key, value, limit)

    def post(self, key, value, limit=FETCH_LIMIT):
        value = urllib.unquote(value).decode('utf-8')

        query = Snippet.all()
        query.filter("{0} =".format(key), value)
        query.order("-date")
        snippets = query.fetch(int(limit))

        template_values = {'snippets': snippets}
        self.render_to_response('list.html', **template_values)
