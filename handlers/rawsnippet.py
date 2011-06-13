import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from model import Snippet

class RawSnippet(webapp.RequestHandler):
    '''
        Get a raw text representation of snippet content

        Processes GET and POST requests.

        Params:
            id --- the unique identifier of snippet entry
    '''

    def get(self):
        self.post()

    def post(self):
        snippet = Snippet.get_by_id(int(self.request.get('id')))

        if snippet is not None:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write(snippet.content)
        else:
            template_values = {'error': 'Snippet with id %s not found' % self.request.get('id')}
            path = os.path.join(os.getcwd(), 'templates', '404.html')

            self.error(404)
            self.response.headers['Content-Type'] = 'text/html'
            self.response.out.write(template.render(path, template_values))

