import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

class MainPage(webapp.RequestHandler):
    '''
        Show the main page where user can enter a new snippet

        Processes GET and POST requests.
    '''

    def get(self):
        path = os.path.join(os.getcwd(), 'templates', 'new.html')

        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(template.render(path, {}))

    def post(self):
        self.get()

