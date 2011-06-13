import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from model import Snippet

class DownloadSnippet(webapp.RequestHandler):
    '''
        Download snippet content as a file

        Processes GET and POST requests.

        Snippet id is specified as url path (part between the host name and params), i.e.:
            GET xsnippet.tk/1/download will return content of snippet with id 1 as a file
    '''

    def get(self, snippetid):
        self.post(snippetid)

    def post(self, snippetid):
        snippet = Snippet.get_by_id(int(snippetid))

        if snippet is not None:
            filename = snippetid
            extension = snippet.extensions[snippet.language] if snippet.language in snippet.extensions else '.txt'
            attachment = 'attachment; filename="%s%s"' % (filename, extension)

            self.response.headers['Content-Type'] = 'text/plain'
            self.response.headers['Content-Disposition'] = attachment
            self.response.out.write(snippet.content)
        else:
            template_values = {'error': 'Snippet with id %s not found' % snippetid}
            path = os.path.join(os.getcwd(), 'templates', '404.html')

            self.error(404)
            self.response.headers['Content-Type'] = 'text/html'
            self.response.out.write(template.render(path, template_values))

