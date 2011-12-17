import os

import webapp2
from google.appengine.ext.webapp import template

from model import Snippet

class RawSnippet(webapp2.RequestHandler):
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
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write(snippet.content)
        else:
            template_values = {'error': 'Snippet with id %s not found' % snippetid}
            path = os.path.join(os.getcwd(), 'templates', '404.html')

            self.error(404)
            self.response.headers['Content-Type'] = 'text/html'
            self.response.write(template.render(path, template_values))

