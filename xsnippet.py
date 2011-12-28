# coding: utf-8
import sys
import os

# add third-party python libs into PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

import webapp2

application = webapp2.WSGIApplication([
    (r'/', 'handlers.MainPage'),
    (r'/about', 'handlers.AboutPage'),
    (r'/upload', 'handlers.UploadPage'),
    (r'/new', 'handlers.NewSnippet'),
    (r'/search', 'handlers.SearchSnippet'),
    (r'/([0-9]+)', 'handlers.ShowSnippet'),
    (r'/([0-9]+)/raw', 'handlers.RawSnippet'),
    (r'/([0-9]+)/download', 'handlers.DownloadSnippet'),
    (r'/([0-9]+)/embed', 'handlers.EmbedSnippet'),
    (r'/recent/?', 'handlers.RecentSnippet'),
    (r'/recent/?(\d+)?', 'handlers.RecentSnippet'),
    (r'/(\w+)/([a-zA-Z0-9_%-]+)/?', 'handlers.ListSnippet'),
    (r'/(\w+)/([a-zA-Z0-9_%-]+)/(\d+)?', 'handlers.ListSnippet'),
    (r'/sitemap.xml', 'handlers.Sitemap')],
    debug=True)
