import os
import urllib

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from model import Snippet

class ListSnippet(webapp.RequestHandler):
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

    def get(self, key, value):
        self.post(key, value)

    def post(self, key, value):
        value = urllib.unquote(value).decode('utf-8')

        query = Snippet.all()
        query.filter("%s =" % key, value)
        snippets = query.fetch(20)

        template_values = {'snippets': snippets}
        path = os.path.join(os.getcwd(), 'templates', 'list.html')

        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(template.render(path, template_values))

