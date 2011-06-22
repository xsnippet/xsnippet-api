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
        if not snippet.author:
            snippet.author = 'Anonymous'

        snippet.title = self.request.get('title')
        if not snippet.title:
            snippet.title = 'Untitled'

        snippet.language = self.request.get('language')
        if not snippet.language:
            snippet.language = 'Text'

        snippet.content = self.request.get('content')

        tags = self.request.get('tags')
        if tags:
            snippet.tags = [tag.lstrip() for tag in tags.split(',')]
        else:
            snippet.tags = []

        snippet.put()

        self.redirect('/' + str(snippet.key().id()))
