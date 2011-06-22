from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from handlers import MainPage
from handlers import NewSnippet
from handlers import ShowSnippet
from handlers import RawSnippet
from handlers import DownloadSnippet
from handlers import ListSnippet

application = webapp.WSGIApplication([('/', MainPage),
                                      ('/new', NewSnippet),
                                      (r'/([0-9]+)', ShowSnippet),
                                      (r'/([0-9]+)/raw', RawSnippet),
                                      (r'/([0-9]+)/download', DownloadSnippet),
                                      (r'/(\w+)/([a-zA-Z0-9_%-]+)/?', ListSnippet),
                                      (r'/(\w+)/([a-zA-Z0-9_%-]+)/(\d+)?', ListSnippet)],
                                      debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

