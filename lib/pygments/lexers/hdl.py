# -*- coding: utf-8 -*-
"""
    pygments.lexers.hdl
    ~~~~~~~~~~~~~~~~~~~

    Lexers for hardware descriptor languages.

    :copyright: Copyright 2010 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, using, this
from pygments.token import \
     Text, Comment, Operator, Keyword, Name, String, Number, Punctuation, \
     Error

__all__ = ['VerilogLexer', 'VhdlLexer']


class VerilogLexer(RegexLexer):
    """
    For verilog source code with preprocessor directives.

    *New in Pygments 1.4.*
    """
    name = 'verilog'
    aliases = ['v']
    filenames = ['*.v', '*.sv']
    mimetypes = ['text/x-verilog']

    #: optional Comment or Whitespace
    _ws = r'(?:\s|//.*?\n|/[*].*?[*]/)+'

    tokens = {
        'root': [
            (r'^\s*`define', Comment.Preproc, 'macro'),
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text), # line continuation
            (r'/(\\\n)?/(\n|(.|\n)*?[^\\]\n)', Comment.Single),
            (r'/(\\\n)?[*](.|\n)*?[*](\\\n)?/', Comment.Multiline),
            (r'[{}#@]', Punctuation),
            (r'L?"', String, 'string'),
            (r"L?'(\\.|\\[0-7]{1,3}|\\x[a-fA-F0-9]{1,2}|[^\\\'\n])'", String.Char),
            (r'(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d+[lL]?', Number.Float),
            (r'(\d+\.\d*|\.\d+|\d+[fF])[fF]?', Number.Float),
            (r'([0-9]+)|(\'h)[0-9a-fA-F]+', Number.Hex),
            (r'([0-9]+)|(\'b)[0-1]+', Number.Hex),   # should be binary
            (r'([0-9]+)|(\'d)[0-9]+', Number.Integer),
            (r'([0-9]+)|(\'o)[0-7]+', Number.Oct),
            (r'\'[01xz]', Number),
            (r'\d+[Ll]?', Number.Integer),
            (r'\*/', Error),
            (r'[~!%^&*+=|?:<>/-]', Operator),
            (r'[()\[\],.;\']', Punctuation),
            (r'`[a-zA-Z_][a-zA-Z0-9_]*', Name.Constant),

            (r'^\s*(package)(\s+)', bygroups(Keyword.Namespace, Text)),
            (r'^\s*(import)(\s+)', bygroups(Keyword.Namespace, Text), 'import'),

            (r'(always|always_comb|always_ff|always_latch|and|assign|automatic|'
             r'begin|break|buf|bufif0|bufif1|case|casex|casez|cmos|const|'
             r'continue|deassign|default|defparam|disable|do|edge|else|end|endcase|'
             r'endfunction|endgenerate|endmodule|endpackage|endprimitive|endspecify|'
             r'endtable|endtask|enum|event|final|for|force|forever|fork|function|'
             r'generate|genvar|highz0|highz1|if|initial|inout|input|'
             r'integer|join|large|localparam|macromodule|medium|module|'
             r'nand|negedge|nmos|nor|not|notif0|notif1|or|output|packed|'
             r'parameter|pmos|posedge|primitive|pull0|pull1|pulldown|pullup|rcmos|'
             r'ref|release|repeat|return|rnmos|rpmos|rtran|rtranif0|'
             r'rtranif1|scalared|signed|small|specify|specparam|strength|'
             r'string|strong0|strong1|struct|table|task|'
             r'tran|tranif0|tranif1|type|typedef|'
             r'unsigned|var|vectored|void|wait|weak0|weak1|while|'
             r'xnor|xor)\b', Keyword),

            (r'(`accelerate|`autoexpand_vectornets|`celldefine|`default_nettype|'
             r'`else|`elsif|`endcelldefine|`endif|`endprotect|`endprotected|'
             r'`expand_vectornets|`ifdef|`ifndef|`include|`noaccelerate|`noexpand_vectornets|'
             r'`noremove_gatenames|`noremove_netnames|`nounconnected_drive|'
             r'`protect|`protected|`remove_gatenames|`remove_netnames|`resetall|'
             r'`timescale|`unconnected_drive|`undef)\b', Comment.Preproc),

            (r'(\$bits|\$bitstoreal|\$bitstoshortreal|\$countdrivers|\$display|\$fclose|'
             r'\$fdisplay|\$finish|\$floor|\$fmonitor|\$fopen|\$fstrobe|\$fwrite|'
             r'\$getpattern|\$history|\$incsave|\$input|\$itor|\$key|\$list|\$log|'
             r'\$monitor|\$monitoroff|\$monitoron|\$nokey|\$nolog|\$printtimescale|'
             r'\$random|\$readmemb|\$readmemh|\$realtime|\$realtobits|\$reset|\$reset_count|'
             r'\$reset_value|\$restart|\$rtoi|\$save|\$scale|\$scope|\$shortrealtobits|'
             r'\$showscopes|\$showvariables|\$showvars|\$sreadmemb|\$sreadmemh|'
             r'\$stime|\$stop|\$strobe|\$time|\$timeformat|\$write)\b', Name.Builtin),

            (r'(class)(\s+)', bygroups(Keyword, Text), 'classname'),
            (r'(byte|shortint|int|longint|interger|time|'
             r'bit|logic|reg|'
             r'supply0|supply1|tri|triand|trior|tri0|tri1|trireg|uwire|wire|wand|wor'
             r'shortreal|real|realtime)\b', Keyword.Type),
            ('[a-zA-Z_][a-zA-Z0-9_]*:(?!:)', Name.Label),
            ('[a-zA-Z_][a-zA-Z0-9_]*', Name),
        ],
        'classname': [
            (r'[a-zA-Z_][a-zA-Z0-9_]*', Name.Class, '#pop'),
        ],
        'string': [
            (r'"', String, '#pop'),
            (r'\\([\\abfnrtv"\']|x[a-fA-F0-9]{2,4}|[0-7]{1,3})', String.Escape),
            (r'[^\\"\n]+', String), # all other characters
            (r'\\\n', String), # line continuation
            (r'\\', String), # stray backslash
        ],
        'macro': [
            (r'[^/\n]+', Comment.Preproc),
            (r'/[*](.|\n)*?[*]/', Comment.Multiline),
            (r'//.*?\n', Comment.Single, '#pop'),
            (r'/', Comment.Preproc),
            (r'(?<=\\)\n', Comment.Preproc),
            (r'\n', Comment.Preproc, '#pop'),
        ],
        'import': [
            (r'[a-zA-Z0-9_:]+\*?', Name.Namespace, '#pop')
        ]
    }

    def get_tokens_unprocessed(self, text):
        for index, token, value in \
            RegexLexer.get_tokens_unprocessed(self, text):
            # Convention: mark all upper case names as constants
            if token is Name:
                if value.isupper():
                    token = Name.Constant
            yield index, token, value


class VhdlLexer(RegexLexer):
    """
    For vhdl source code.
    """
    name = 'vhdl'
    aliases = ['vhdl']
    filenames = ['*.vhdl', '*.vhd']
    mimetypes = ['text/x-vhdl']

    tokens = {
        'root': [
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text), # line continuation
            (r'--(?![!#$%&*+./<=>?@\^|_~]).*?$', Comment.Single),
            (r"'(U|X|0|1|Z|W|L|H|-)'", String.Char),
            (r'[~!%^&*+=|?:<>/-]', Operator),
            (r"'[a-zA-Z_][a-zA-Z0-9_]*", Name.Attribute),
            (r'[()\[\],.;\']', Punctuation),
            (r'"[^\n\\]*"', String),

            (r'(library)(\s+)([a-zA-Z_][a-zA-Z0-9_]*)', bygroups(Keyword, Text, Name.Namespace)),
            (r'(use)(\s+)([a-zA-Z_][\.a-zA-Z0-9_]*)', bygroups(Keyword, Text, Name.Namespace)),
            (r'(entity|component)(\s+)([a-zA-Z_][a-zA-Z0-9_]*)', bygroups(Keyword, Text, Name.Class)),
            (r'(architecture|configuration)(\s+)([a-zA-Z_][a-zA-Z0-9_]*)(\s+)(of)(\s+)([a-zA-Z_][a-zA-Z0-9_]*)(\s+)(is)',
                bygroups(Keyword, Text, Name.Class, Text, Keyword, Text, Name.Class, Text, Keyword)),

            (r'(end)(\s+)', bygroups(using(this), Text), 'endblock'),

            include('types'),
            include('keywords'),
            include('numbers'),

            (r'[a-zA-Z_][a-zA-Z0-9_]*', Name),
        ],
        'endblock': [
            (r'\s+$', Text),
            (r'[()\[\],.;\']', Punctuation),

            include('keywords'),
            (r'[a-zA-Z_][a-zA-Z0-9_]*', Name.Class),
        ],
        'types': [
            (r'(boolean|bit|character|severity_level|integer|time|delay_length|'
             r'natural|positive|string|bit_vector|file_open_kind|file_open_status|'
             r'std_ulogic|std_ulogic_vector|std_logic|std_logic_vector)\b', Keyword.Type),
        ],
        'keywords': [
            (r'(abs|access|after|alias|all|and|'
             r'architecture|array|assert|attribute|begin|block|'
             r'body|buffer|bus|case|component|configuration|'
             r'constant|disconnect|downto|else|elsif|end|'
             r'entity|exit|file|for|function|generate|'
             r'generic|group|guarded|if|impure|in|'
             r'inertial|inout|is|label|library|linkage|'
             r'literal|loop|map|mod|nand|new|'
             r'next|nor|not|null|of|on|'
             r'open|or|others|out|package|port|'
             r'postponed|procedure|process|pure|range|record|'
             r'register|reject|return|rol|ror|select|'
             r'severity|signal|shared|sla|sli|sra|'
             r'srl|subtype|then|to|transport|type|'
             r'units|until|use|variable|wait|when|'
             r'while|with|xnor|xor)\b', Keyword),
        ],
        'numbers': [
            (r'\d{1,2}#[0-9a-fA-F_]+#?', Number.Integer),
            (r'[0-1_]+(\.[0-1_])', Number.Integer),
            (r'\d+', Number.Integer),
            (r'(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d+', Number.Float),
            (r'H"[0-9a-fA-F_]+"', Number.Oct),
            (r'O"[0-7_]+"', Number.Oct),
            (r'B"[0-1_]+"', Number.Oct),
        ],
    }


