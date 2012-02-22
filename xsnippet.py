# coding: utf-8
import sys
import os

# add third-party python libs into PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

import webapp2

application = webapp2.WSGIApplication([
    (r'/', 'handlers.index'),
    (r'/about', 'handlers.about'),
    (r'/new', 'handlers.new_snippet'),
    (r'/upload', 'handlers.upload'),
    (r'/tools', 'handlers.tools'),
    (r'/([0-9]+)', 'handlers.show_snippet'),
    (r'/([0-9]+)/raw', 'handlers.raw_snippet'),
    (r'/([0-9]+)/png', 'handlers.png_snippet'),
    (r'/([0-9]+)/download', 'handlers.download_snippet'),
    (r'/([0-9]+)/embed', 'handlers.embed_snippet'),
    (r'/search', 'handlers.search_snippet'),
    (r'/recent/?', 'handlers.recent_snippet'),
    (r'/recent/?(\d+)?', 'handlers.recent_snippet'),
    (r'/recent/?(\d+)?/?(\d+)?', 'handlers.recent_snippet'),
    (r'/(\w+)/([^/]+)/?', 'handlers.list_snippet'),
    (r'/(\w+)/([^/]+)/(\d+)?', 'handlers.list_snippet'),
    (r'/(\w+)/([^/]+)/(\d+)/(\d+)?', 'handlers.list_snippet'),
    (r'/sitemap.xml', 'handlers.sitemap')],
    debug=False)

application.error_handlers[404] = 'handlers.handler_404'
