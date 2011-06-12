import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from model import Snippet

class ShowSnippet(webapp.RequestHandler):
    '''
        Get and show desired snippet

        Retrieve snippet from datastore by id and show it. 

        Processes GET request.

        Params:
            url      --- a url path must represent a unique snippet identifier.
    '''

    def get(self):
        snippet = Snippet().get_by_id(int(self.request.path.lstrip('/')))
        path = os.path.join(os.getcwd(), 'templates', 'show.html')

        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(template.render(path, {'snippet' : snippet}))

