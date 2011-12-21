# coding: utf-8
from basehandler import BaseHandler
from model import Snippet


class DownloadSnippet(BaseHandler):
    '''
        Download snippet content as a file

        Processes GET and POST requests.

        Snippet id is specified as url path (part between the host name and params), i.e.:
            GET xsnippet.org/1/download will return content of snippet with id 1 as a file
    '''

    def get(self, snippetid):
        self.post(snippetid)

    def post(self, snippetid):
        snippet = Snippet.get_by_id(int(snippetid))

        if snippet is not None:
            filename = snippetid
            extension = snippet.extensions[snippet.language] if snippet.language in snippet.extensions else '.txt'
            attachment = 'attachment; filename="{0}{1}"'.format(filename, extension)

            self.response.headers['Content-Type'] = 'text/plain'
            self.response.headers['Content-Disposition'] = attachment
            self.response.write(snippet.content)
        else:
            self.error(404)
            template_values = {'error': 'Snippet with id {0} not found'.format(snippetid)}
            self.render_to_response('404.html', **template_values)
