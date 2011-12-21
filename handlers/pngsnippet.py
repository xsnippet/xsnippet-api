# coding: utf-8
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import ImageFormatter

from basehandler import BaseHandler
from model import Snippet


class PngSnippet(BaseHandler):
    '''
        Show image (png) with highlighted code of snippet.

        Processes GET and POST requests.

        Snippet id is specified as url path (part between the host name and params), i.e.:
            GET xsnippet.org/1/png will return image for snippet with id 1
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

            formatter = ImageFormatter(font_name='Ubuntu Mono')
            png_code = highlight(snippet.content, lexer, formatter)

            self.response.headers['Content-Type'] = 'image/png'
            self.response.write(png_code)

        else:
            self.error(404)
            template_values = {'error': 'Snippet with id {0} not found'.format(snippetid)}
            self.render_to_response('404.html', **template_values)
