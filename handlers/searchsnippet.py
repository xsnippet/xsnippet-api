# coding: utf-8
import re

from basehandler import BaseHandler
from model import Snippet


class SearchSnippet(BaseHandler):
    '''
        Return the list of snippets that meet the given requirements (author, language, etc)

        Processes GET and POST requests.

        Requirements are specified in search request, i.e. a query:
            author:James Black,tags:coolstuff,language:C++
        will return a list of all code snippets written by James Black
        in C++ and tagged as 'coolstuff' (all conditions should be fulfiled)

        NOTE: the delimeter is a ',' character

        List of snippet properties consits of:
            language
            author
            tags
            title
    '''

    FETCH_LIMIT = 100

    def get(self, limit=FETCH_LIMIT):
        self.post(limit)

    def post(self, limit=FETCH_LIMIT):
        querystr = self.request.get('search')

        pattern = ur'(author|language|tags|title):([^,]+),?'
        conditions = re.findall(pattern, querystr)

        query = Snippet.all()
        for key, value in conditions:
            query.filter('{0} ='.format(key), value)
        query.order('-date')
        snippets = query.fetch(int(limit))

        template_values = {'snippets': snippets}
        self.render_to_response('list.html', **template_values)
