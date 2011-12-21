# coding: utf-8
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter

from basehandler import BaseHandler
from model import Snippet


class ShowSnippet(BaseHandler):
    '''
        Show the highlighted code of snippet and additional information

        Processes GET and POST requests.

        Snippet id is specified as url path (part between the host name and params), i.e.:
            GET xsnippet.org/1 will return page for snippet with id 1
    '''

    def get(self, snippetid):
        self.post(snippetid)

    def post(self, snippetid):
        snippet = Snippet.get_by_id(int(snippetid))

        if snippet is not None:
            # pygments highlighting
            languagehl = Snippet.languages[snippet.language]

            if languagehl:
                lexer = get_lexer_by_name(languagehl, stripall=True)
            else:
                lexer = guess_lexer(snippet.content)

            formatter = HtmlFormatter(linenos='table')
            snippet.content = highlight(snippet.content, lexer, formatter)

            template_values = {'snippet': snippet}
            template = 'show.html'
        else:
            template_values = {'error': 'Snippet with id {0} not found'.format(snippetid)}
            template = '404.html'
            self.error(404)

        self.render_to_response(template, **template_values)
