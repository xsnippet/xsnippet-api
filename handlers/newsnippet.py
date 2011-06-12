from google.appengine.ext import webapp

from model import Snippet

class NewSnippet(webapp.RequestHandler):
    '''
        Create a new snippet entry

        Creates a snippet entry given the information (content, language, etc)
        and saves it into the datastore. Each snippet entry gets assigned a unique
        identifier which is used to retrieve it later.

        Processes GET and POST requests.

        Params:
            author   --- an author of snippet
            title    --- a title of snippet
            language --- a language of snippet
            content  --- a text of snippet
            tags     --- a list of strings separated by commas

        Redirect:
            When a snippet is put into the datastore user gets redirected
            to the page showing the highlighted content of the snippet.
    '''

    def get(self):
        self.post()

    def post(self):
        snippet = Snippet()
        snippet.author = self.request.get('author')
        snippet.title = self.request.get('title')
        snippet.language = self.request.get('language')
        snippet.content = self.request.get('content')
        snippet.tags = self.request.get('tags').split(',')
        snippet.put()

        self.redirect('/' + str(snippet.key().id()))

