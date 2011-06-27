import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from model import Snippet

class EmbedSnippet(webapp.RequestHandler):
    '''
        Get a javascript code for pasting snippet anywhere on the web.

        Processes GET and POST requests.

        Snippet id is specified as url path (part between the host name and params), i.e.:
            GET xsnippet.tk/1/embed will return js code for pasting snippet on your page
    '''

    @staticmethod
    def escape(text):
        escape_table = {
            "\\": "\\\\",
            "'": r"\'",
            ">": "&gt;",
            "<": "&lt;",
        }

        for k, v in escape_table.items():
            text = text.replace(k, v)
        return text

    def get(self, snippetid):
        self.post(snippetid)

    def post(self, snippetid):
        snippet = Snippet.get_by_id(int(snippetid))

        if snippet is not None:
            self.response.headers['Content-Type'] = 'text/html'

            code = r"\n".join(EmbedSnippet.escape(line) for line in snippet.content.splitlines())
            #code = EmbedSnippet.escape(code)

            html = \
            '''
              <link rel="stylesheet" href="http://www.xsnippet.tk/static/highlight.js/styles/xsnippet.css">
              <script src="http://www.xsnippet.tk/static/highlight.js/highlight.pack.js"></script>
              <pre><code id="xsnippet_%s" class="%s">%s</code></pre>
              <script>
                  hljs.tabReplace = "    ";
                  var code = document.getElementById("xsnippet_%s");
                  hljs.highlightBlock(code);
              </script>
            ''' % (snippetid, Snippet.languages[snippet.language], code, snippetid)

            js = "document.write('%s');" % (''.join(html.splitlines()))
            self.response.out.write(js)

        else:
            template_values = {'error': 'Snippet with id %s not found' % snippetid}
            path = os.path.join(os.getcwd(), 'templates', '404.html')

            self.error(404)
            self.response.headers['Content-Type'] = 'text/html'
            self.response.out.write(template.render(path, template_values))

