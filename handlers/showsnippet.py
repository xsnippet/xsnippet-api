import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from model import Snippet

class ShowSnippet(webapp.RequestHandler):
    '''
        Show the highlighted code of snippet and additional information

        Processes GET and POST requests.

        Snippet id is specified as url path (part between the host name and params), i.e.:
            GET xsnippet.tk/1 will return page for snippet with id 1
    '''

    def get(self, snippetid):
        self.post(snippetid)

    def post(self, snippetid):
        snippet = Snippet.get_by_id(int(snippetid))

        if snippet is not None:
            # get language highlight.js name
            languagehl = Snippet.languages[snippet.language]

            template_values = {'snippet': snippet, 'languagehl': languagehl}
            path = os.path.join(os.getcwd(), 'templates', 'show.html')
        else:
            template_values = {'error': 'Snippet with id %s not found' % snippetid}
            path = os.path.join(os.getcwd(), 'templates', '404.html')
            self.error(404)

        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(template.render(path, template_values))

