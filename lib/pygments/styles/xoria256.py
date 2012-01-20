# -*- coding: utf-8 -*-
"""
    Xoria256 Colorscheme
    ~~~~~~~~~~~~~~~~~~~~

    Converted by Vim Colorscheme Converter
"""
from pygments.style import Style
from pygments.token import Token, Comment, Name, Keyword, Generic, Number, Operator, String

class Xoria256Style(Style):

    background_color = '#1c1c1c'
    styles = {
        Token:              'noinherit #d0d0d0 bg:#1c1c1c',
        Generic.Emph:       '#00afff underline',
        Generic.Output:     '#9e9e9e bg:#121212 bold',
        Keyword.Type:       'noinherit #afafdf',
        Generic.Deleted:    'noinherit bg:#949494',
        Name.Variable:      'noinherit #dfafdf',
        Generic.Traceback:  '#ffffff bg:#800000',
        Number:             '#dfaf87',
        Name.Tag:           'noinherit #87afdf',
        Keyword:            'noinherit #87afdf',
        Generic.Error:      '#ffffff bg:#800000',
        Comment:            '#808080',
        Name.Entity:        '#df8787',
        Comment.Preproc:    '#afdf87',
        Generic.Inserted:   'bg:#afdfaf',
        Generic.Subheading: '#ffdfff',
        Generic.Heading:    '#ffdfff',
        Name.Constant:      '#ffffaf',
    }
