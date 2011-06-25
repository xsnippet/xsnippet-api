import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from model import Snippet

class Sitemap(webapp.RequestHandler):
    '''
        Generate sitemap.xml.

        Processes GET and POST requests.
    '''

    def get(self):
        self.post()

    def post(self):

        snippets = Snippet.all().order('-date')

        template_values = {'snippets': snippets}
        path = os.path.join(os.getcwd(), 'templates', 'sitemap.xml')

        self.response.headers['Content-Type'] = 'text/xml'
        self.response.out.write(template.render(path, template_values))

