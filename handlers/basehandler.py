# coding: utf-8

import webapp2
from webapp2_extras import jinja2


class BaseHandler(webapp2.RequestHandler):
    '''
        Base class which provide method for rendering templates.
    '''

    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(app=self.app)

    def render_to_response(self, template, **context):
        response = self.jinja2.render_template(template, **context);
        self.response.write(response)
