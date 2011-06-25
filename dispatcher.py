from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from handlers import MainPage
from handlers import NewSnippet
from handlers import ShowSnippet
from handlers import RawSnippet
from handlers import DownloadSnippet
from handlers import ListSnippet
from handlers import RecentSnippet
from handlers import Sitemap

application = webapp.WSGIApplication([(r'/', MainPage),
                                      (r'/new', NewSnippet),
                                      (r'/([0-9]+)', ShowSnippet),
                                      (r'/([0-9]+)/raw', RawSnippet),
                                      (r'/([0-9]+)/download', DownloadSnippet),
                                      (r'/recent/?', RecentSnippet),
                                      (r'/recent/?(\d+)?', RecentSnippet),
                                      (r'/(\w+)/([a-zA-Z0-9_%-]+)/?', ListSnippet),
                                      (r'/(\w+)/([a-zA-Z0-9_%-]+)/(\d+)?', ListSnippet),
                                      (r'/sitemap.xml', Sitemap)],
                                      debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

