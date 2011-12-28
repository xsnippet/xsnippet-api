# coding: utf-8
import os
import re
import urllib

import webapp2
from webapp2_extras import jinja2

from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter

from model import Snippet

#
# Settings
#

FETCH_LIMIT = 20


#
# Auxiliary functions
#

def create_response(headers, content):
    '''
        @TODO: comment
    '''
    response = webapp2.Response()
    for key,value in headers.items():
        response.headers[key] = value
    response.write(content)
    return response


def render_to_response(template, **context):
    '''
        @TODO: comment
    '''
    jinja = jinja2.get_jinja2(app=webapp2.get_app())    # cache?
    return create_response(
        {'Content-Type': 'text/html; charset=utf-8'},
        jinja.render_template(template, **context)
    )


#
# Request Handlers
#

def index(request):
    '''Render index page (new snippet) template.'''
    return render_to_response('new.html')


def about(request):
    '''Render about page template.'''
    return render_to_response('about.html')


def upload(request):
    '''Render upload page template.'''
    return render_to_response('upload.html')


def new_snippet(request):
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
    snippet = Snippet()

    snippet.author = request.get('author')
    if not snippet.author:
        snippet.author = 'Anonymous'

    snippet.title = request.get('title')
    if not snippet.title:
        snippet.title = 'Untitled'

    snippet.language = request.get('language')
    if not snippet.language:
        snippet.language = 'Text'

    tags = request.get('tags')
    if tags:
        snippet.tags = [tag.lstrip() for tag in tags.split(',')]
    else:
        snippet.tags = []

    filedata = request.get('file')
    if filedata:
        snippet.content = filedata.decode('utf-8')

        # get the name of uploaded file from request body
        body = urllib.unquote(request.body)
        info = re.match(r"file=FieldStorage\('file',\+'(.*)'\)", body)
        filename, extension = os.path.splitext(info.groups(0)[0])

        if snippet.title == 'Untitled':
            snippet.title = filename
        snippet.language = Snippet.extensions_reverse.get(extension, 'Text')
    else:
        snippet.content = request.get('content')

    if snippet.content:
        snippet.put()
        return webapp2.redirect('/' + str(snippet.key().id()))
    else:
        return webapp2.redirect('/')


def show_snippet(request, snippetid):
    '''
        Show the highlighted code of snippet and additional information

        Processes GET and POST requests.

        Snippet id is specified as url path (part between the host name and params), i.e.:
            GET xsnippet.org/1 will return page for snippet with id 1
    '''

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
        return render_to_response('show.html', snippet=snippet)
    else:
        return webapp2.abort(404, 'Snippet with id {0} not found'.format(snippetid))


def raw_snippet(request, snippetid):
    '''
        Get a raw text representation of snippet content

        Processes GET and POST requests.

        Snippet id is specified as url path (part between the host name and params), i.e.:
            GET xsnippet.org/1/raw will return text content of snippet with id 1
    '''
    snippet = Snippet.get_by_id(int(snippetid))

    if snippet is not None:
        return create_response(
            {'Content-Type': 'text/plain; charset=utf-8'},
            snippet.content
        )
    else:
        return webapp2.abort(404, 'Snippet with id {0} not found'.format(snippetid))


def download_snippet(request, snippetid):
    '''
        Download snippet content as a file

        Processes GET and POST requests.

        Snippet id is specified as url path (part between the host name and params), i.e.:
            GET xsnippet.org/1/download will return content of snippet with id 1 as a file
    '''
    snippet = Snippet.get_by_id(int(snippetid))

    if snippet is not None:
        filename = snippetid
        extension = snippet.extensions[snippet.language] if snippet.language in snippet.extensions else '.txt'
        attachment = 'attachment; filename="{0}{1}"'.format(filename, extension)

        return create_response(
            {'Content-Type': 'text/plain; charset=utf-8', 'Content-Disposition': attachment},
            snippet.content
        )
    else:
        return webapp2.abort(404, 'Snippet with id {0} not found'.format(snippetid))


def embed_snippet(request, snippetid):
    '''
        Get a javascript code for pasting snippet anywhere on the web.

        Processes GET and POST requests.

        Snippet id is specified as url path (part between the host name and params), i.e.:
            GET xsnippet.org/1/embed will return js code for pasting snippet on your page
    '''
    snippet = Snippet.get_by_id(int(snippetid))

    if snippet is not None:
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
        return create_response({'Content-Type': 'text/html; charset=utf-8'}, js)
    else:
        return webapp2.abort(404, 'Snippet with id {0} not found'.format(snippetid))


def search_snippet(request, limit=FETCH_LIMIT):
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
    limit = int(limit)
    if limit > FETCH_LIMIT:
        limit = FETCH_LIMIT

    querystr = request.get('search')
    pattern = ur'(author|language|tags|title):([^,]+),?'
    conditions = re.findall(pattern, querystr)

    query = Snippet.all()
    for key, value in conditions:
        query.filter('{0} ='.format(key), value)
    query.order('-date')
    snippets = query.fetch(limit)
    return render_to_response('list.html', snippets=snippets)


def recent_snippet(request, limit=FETCH_LIMIT):
    '''
        Return the list of recently posted snippets.

        The number of snippets to show is specified as url path, i.e. :
            GET xsnippet.org/recent/15
        will return a list of 15 posted last snippets. But the number of
        snippets can't exceed the FETCH_LIMIT (currently 20, but it is
        a subject to change)

        Processes GET and POST requests.
    '''
    limit = int(limit)
    if limit > FETCH_LIMIT:
        limit = FETCH_LIMIT

    query = Snippet.all()
    query.order("-date")
    snippets = query.fetch(limit)

    return render_to_response('list.html', snippets=snippets)


def list_snippet(request, key, value, limit=FETCH_LIMIT):

    limit = int(limit)
    if limit > FETCH_LIMIT:
        limit = FETCH_LIMIT

    value = urllib.unquote(value).decode('utf-8')

    query = Snippet.all()
    query.filter("{0} =".format(key), value)
    query.order("-date")
    snippets = query.fetch(int(limit))
    return render_to_response('list.html', snippets=snippets)


def sitemap(request):
    '''
        Generate sitemap.xml.

        Processes GET and POST requests.
    '''
    keys = Snippet.all(keys_only=True).order("-date")
    jinja = jinja2.get_jinja2(app=webapp2.get_app())
    return create_response(
        {'Content-Type': 'text/xml; charset=utf-8'},
        jinja.render_template('sitemap.xml', keys=keys)
    )


def handler_404(request, response, exception):
    response.set_status(404)
    return render_to_response('error.html', error_code=404, error=exception.detail)
