# coding: utf-8
from basehandler import BaseHandler


class UploadPage(BaseHandler):
    '''
        Show the upload page where user can upload a file snippet

        Processes GET and POST requests.
    '''

    def get(self):
        self.post()

    def post(self):
        self.render_to_response('upload.html', **{})
