import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from model import Snippet

class ShowSnippet(webapp.RequestHandler):
    '''
        Show the highlighted code of snippet and additional information

        Processes GET and POST requests.

        Params:
            id --- the unique identifier of a snippet entry
    '''

    def get(self):
        self.post()

    def post(self):
        snippet = Snippet.get_by_id(int(self.request.get('id')))

        if snippet is not None:
            template_values = {'snippet': snippet}
            path = os.path.join(os.getcwd(), 'templates', 'show.html')
        else:
            template_values = {'error': 'Snippet with id %s not found' % self.request.get('id')}
            path = os.path.join(os.getcwd(), 'templates', '404.html')

        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(template.render(path, template_values))

