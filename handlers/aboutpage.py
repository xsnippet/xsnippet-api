import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

class AboutPage(webapp.RequestHandler):
    '''
        Renders about page template.
    '''

    def get(self):
        self.post()

    def post(self):
        path = os.path.join(os.getcwd(), 'templates', 'about.html')
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(template.render(path, {}))

