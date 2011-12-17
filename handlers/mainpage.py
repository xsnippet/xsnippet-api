import os

import webapp2
from google.appengine.ext.webapp import template

class MainPage(webapp2.RequestHandler):
    '''
        Show the main page where user can enter a new snippet

        Processes GET and POST requests.
    '''

    def get(self):
        path = os.path.join(os.getcwd(), 'templates', 'new.html')

        self.response.headers['Content-Type'] = 'text/html'
        self.response.write(template.render(path, {}))

    def post(self):
        self.get()

