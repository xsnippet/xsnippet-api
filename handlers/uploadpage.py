import os

import webapp2
from google.appengine.ext.webapp import template

class UploadPage(webapp2.RequestHandler):
    '''
        Show the upload page where user can upload a file snippet

        Processes GET and POST requests.
    '''

    def get(self):
        path = os.path.join(os.getcwd(), 'templates', 'upload.html')

        self.response.headers['Content-Type'] = 'text/html'
        self.response.write(template.render(path, {}))

    def post(self):
        self.get()

