# coding: utf-8
from basehandler import BaseHandler
from model import Snippet


class RawSnippet(BaseHandler):
    '''
        Get a raw text representation of snippet content

        Processes GET and POST requests.

        Snippet id is specified as url path (part between the host name and params), i.e.:
            GET xsnippet.org/1/raw will return text content of snippet with id 1
    '''

    def get(self, snippetid):
        self.post(snippetid)

    def post(self, snippetid):
        snippet = Snippet.get_by_id(int(snippetid))

        if snippet is not None:
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write(snippet.content)
        else:
            self.error(404)
            template_values = {'error': 'Snippet with id {0} not found'.format(snippetid)}
            self.render_to_response('404.html', **template_values)
