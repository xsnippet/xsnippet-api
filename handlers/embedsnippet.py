import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter

from model import Snippet

class EmbedSnippet(webapp.RequestHandler):
    '''
        Get a javascript code for pasting snippet anywhere on the web.

        Processes GET and POST requests.

        Snippet id is specified as url path (part between the host name and params), i.e.:
            GET xsnippet.tk/1/embed will return js code for pasting snippet on your page
    '''

    def get(self, snippetid):
        self.post(snippetid)

    def post(self, snippetid):
        snippet = Snippet.get_by_id(int(snippetid))

        if snippet is not None:
            self.response.headers['Content-Type'] = 'text/html'

            languagehl = Snippet.languages[snippet.language]

            if languagehl:
                lexer = get_lexer_by_name(languagehl, stripall=True)
            else:
                lexer = guess_lexer(snippet.content)

            formatter = HtmlFormatter(linenos='table')
            snippet.content = highlight(snippet.content, lexer, formatter)

            html = \
            '''
              <link rel="stylesheet" href="http://localhost:8080/static/pygments/styles/colorful.css">
              <link rel="stylesheet" href="http://localhost:8080/static/styles/embed.css">
              %s
            ''' % (snippet.content)

            js = "document.write('%s');" % (r'\n'.join(html.splitlines()))
            self.response.out.write(js)

        else:
            template_values = {'error': 'Snippet with id %s not found' % snippetid}
            path = os.path.join(os.getcwd(), 'templates', '404.html')

            self.error(404)
            self.response.headers['Content-Type'] = 'text/html'
            self.response.out.write(template.render(path, template_values))

