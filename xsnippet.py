import sys
import os

# add third-party python libs into PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

import webapp2

from handlers import MainPage
from handlers import AboutPage
from handlers import UploadPage
from handlers import NewSnippet
from handlers import ShowSnippet
from handlers import RawSnippet
from handlers import DownloadSnippet
from handlers import EmbedSnippet
from handlers import PngSnippet
from handlers import ListSnippet
from handlers import SearchSnippet
from handlers import RecentSnippet
from handlers import Sitemap

application = webapp2.WSGIApplication([(r'/', MainPage),
                                       (r'/about', AboutPage),
                                       (r'/upload', UploadPage),
                                       (r'/new', NewSnippet),
                                       (r'/search', SearchSnippet),
                                       (r'/([0-9]+)', ShowSnippet),
                                       (r'/([0-9]+)/raw', RawSnippet),
                                       (r'/([0-9]+)/download', DownloadSnippet),
                                       (r'/([0-9]+)/embed', EmbedSnippet),
                                       (r'/([0-9]+)/png', PngSnippet),
                                       (r'/recent/?', RecentSnippet),
                                       (r'/recent/?(\d+)?', RecentSnippet),
                                       (r'/(\w+)/([a-zA-Z0-9_%-]+)/?', ListSnippet),
                                       (r'/(\w+)/([a-zA-Z0-9_%-]+)/(\d+)?', ListSnippet),
                                       (r'/sitemap.xml', Sitemap)],
                                       debug=True)
