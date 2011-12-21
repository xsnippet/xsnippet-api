# coding: utf-8
from basehandler import BaseHandler


class AboutPage(BaseHandler):
    '''
        Renders about page template.
    '''

    def get(self):
        self.post()

    def post(self):
        self.render_to_response('about.html', **{})
