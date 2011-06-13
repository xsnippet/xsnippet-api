from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from handlers import MainPage
from handlers import NewSnippet
from handlers import ShowSnippet
from handlers import RawSnippet
from handlers import DownloadSnippet

application = webapp.WSGIApplication([('/', MainPage),
                                      ('/new', NewSnippet),
                                      ('/[0-9]+', ShowSnippet),
                                      ('/[0-9]+/raw', RawSnippet),
                                      ('/[0-9]+/download', DownloadSnippet)],
                                      debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

