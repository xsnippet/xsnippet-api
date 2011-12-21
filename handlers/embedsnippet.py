# coding: utf-8
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter

from basehandler import BaseHandler
from model import Snippet


class EmbedSnippet(BaseHandler):
    '''
        Get a javascript code for pasting snippet anywhere on the web.

        Processes GET and POST requests.

        Snippet id is specified as url path (part between the host name and params), i.e.:
            GET xsnippet.org/1/embed will return js code for pasting snippet on your page
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
              <link rel="stylesheet" href="http://www.xsnippet.org/static/pygments/styles/colorful.css">
              <link rel="stylesheet" href="http://www.xsnippet.org/static/styles/embed.css">
              {0}
            '''.format(snippet.content)

            js = "document.write('{0}');".format(r'\n'.join(html.splitlines()))
            self.response.write(js)

        else:
            self.error(404)
            template_values = {'error': 'Snippet with id {0} not found'.format(snippetid)}
            self.render_to_response('404.html', **template_values)
