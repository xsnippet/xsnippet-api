# coding: utf-8
from basehandler import BaseHandler


class MainPage(BaseHandler):
    '''
        Show the main page where user can enter a new snippet

        Processes GET and POST requests.
    '''

    def get(self):
        self.post()

    def post(self):
        self.render_to_response('new.html', **{})
