# coding: utf-8
from basehandler import BaseHandler
from model import Snippet


class Sitemap(BaseHandler):
    '''
        Generate sitemap.xml.

        Processes GET and POST requests.
    '''

    def get(self):
        self.post()

    def post(self):
        keys = Snippet.all(keys_only=True).order("-date")
        template_values = {'keys': keys}
        self.render_to_response('sitemap.xml', **template_values)
