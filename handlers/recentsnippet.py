import os

import webapp2
from google.appengine.ext.webapp import template

from model import Snippet

class RecentSnippet(webapp2.RequestHandler):
    '''
        Return the list of recently posted snippets.

        The number of snippets to show is specified as url path, i.e. :
            GET xsnippet.org/recent/15
        will return a list of 15 posted last snippets. But the number of
        snippets can't exceed the FETCH_LIMIT (currently 20, but it is
        a subject to change)

        Processes GET and POST requests.
    '''

    FETCH_LIMIT = 20

    def get(self, limit=FETCH_LIMIT):
        self.post(limit)

    def post(self, limit=FETCH_LIMIT):
        limit = int(limit)
        if limit > RecentSnippet.FETCH_LIMIT:
            limit = RecentSnippet.FETCH_LIMIT

        query = Snippet.all()
        query.order("-date")
        snippets = query.fetch(int(limit))

        template_values = {'snippets': snippets}
        path = os.path.join(os.getcwd(), 'templates', 'list.html')

        self.response.headers['Content-Type'] = 'text/html'
        self.response.write(template.render(path, template_values))

