import os

import webapp2
from google.appengine.ext.webapp import template

class AboutPage(webapp2.RequestHandler):
    '''
        Renders about page template.
    '''

    def get(self):
        self.post()

    def post(self):
        path = os.path.join(os.getcwd(), 'templates', 'about.html')
        self.response.headers['Content-Type'] = 'text/html'
        self.response.write(template.render(path, {}))

