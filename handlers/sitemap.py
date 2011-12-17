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
        keys = Snippet.all(keys_only=True).order("-date")

        template_values = {'keys': keys}
        path = os.path.join(os.getcwd(), 'templates', 'sitemap.xml')

        self.response.headers['Content-Type'] = 'text/xml'
        self.response.write(template.render(path, template_values))

