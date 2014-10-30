# coding: utf-8
"""
    xsnippet.db.models
    ~~~~~~~~~~~~~~~~~~

    The module provides a database related settings:

    * SQLAlchemy configuration;
    * ORM classes

    :copyright: (c) 2014, XSnippet Team
    :license: BSD, see LICENSE for details
"""
import datetime

import sqlalchemy as sa
import sqlalchemy.orm as orm
import sqlalchemy.ext.declarative as declarative

from flask.ext.sqlalchemy import SQLAlchemy


naming_convention = {
    'ix': 'ix_%(table_name)s_%(column_0_label)s',
    'uq': 'uq_%(table_name)s_%(column_0_name)s',
    'ck': 'ck_%(table_name)s_%(constraint_name)s',
    'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s',
}


db = SQLAlchemy()
db.Model.metadata.naming_convention = naming_convention


class Model(db.Model):
    __abstract__ = True

    @declarative.declared_attr
    def __tablename__(cls):
        return cls.__name__.lower() + 's'

    id = sa.Column('id', sa.Integer, primary_key=True)
    created_at = sa.Column('created_at',
                           sa.DateTime(),
                           default=datetime.datetime.utcnow,
                           nullable=False,
                           index=True)
    updated_at = sa.Column('updated_at',
                           sa.DateTime(),
                           default=datetime.datetime.utcnow,
                           onupdate=datetime.datetime.utcnow,
                           nullable=False,
                           index=True)


class Author(Model):
    name = sa.Column('name', sa.String(128), nullable=False, index=True)
    email = sa.Column('email', sa.String(256), nullable=False, index=True)


snippets_tags = sa.Table(
    'snippets_tags', db.Model.metadata,
    sa.Column('snippet_id',
              sa.Integer,
              sa.ForeignKey('snippets.id'),
              nullable=False),
    sa.Column('tag_id',
              sa.Integer,
              sa.ForeignKey('tags.id'),
              nullable=False),
    sa.PrimaryKeyConstraint('snippet_id', 'tag_id')
)


class Tag(Model):
    value = sa.Column('value', sa.String(64), unique=True)
    snippet_id = sa.Column('snippet_id',
                           sa.Integer,
                           sa.ForeignKey('snippets.id'),
                           nullable=False)


class Changeset(Model):
    """Represents history of a snippet versions.

    History is basically a linked list of changesets. Each changesets has a
    pointer to its parent. The base version parent is NULL. The snippet entry
    always points to the latest changeset (at the same time, a user may request
    a particular version of a snippet to be returned).

    """

    parent_id = sa.Column('parent_id',
                          sa.Integer,
                          sa.ForeignKey('changesets.id'),
                          nullable=True)  # NULL for base version
    contents = sa.Column('contents',
                         sa.Text(),
                         nullable=False)

    parent = orm.relationship('Changeset')


class Snippet(Model):
    __table_args__ = (
        sa.Index('ix_snippets_author', 'author_id',
                 postgresql_where=(~sa.sql.column('author_id').is_(None))),
    )

    title = sa.Column('title', sa.String(128), nullable=True, index=True)
    lang = sa.Column('lang', sa.Enum(*["text",
                                       "c",
                                       "cpp",
                                       "objectivec",
                                       "java",
                                       "csharp",
                                       "python",
                                       "python3",
                                       "perl",
                                       "ruby",
                                       "html+php",
                                       "html",
                                       "css",
                                       "javascript",
                                       "sql",
                                       "django",
                                       "erb",
                                       "smarty",
                                       "xml",
                                       "yaml",
                                       "apacheconf",
                                       "nginx",
                                       "lighttpd ",
                                       "delphi",
                                       "vb.net",
                                       "common-lisp",
                                       "haskell",
                                       "d",
                                       "go",
                                       "gas",
                                       "nasm",
                                       "actionscript",
                                       "ada",
                                       "applescript",
                                       "asymptote",
                                       "boo",
                                       "bro",
                                       "brainfuck",
                                       "clojure",
                                       "coffeescript",
                                       "coq",
                                       "cython",
                                       "dart",
                                       "dylan",
                                       "erlang",
                                       "elixir",
                                       "factor",
                                       "fancy",
                                       "fortran",
                                       "fsharp",
                                       "felix",
                                       "gnuplot",
                                       "gherkin",
                                       "glsl",
                                       "groovy",
                                       "io",
                                       "llvm",
                                       "lua",
                                       "newlisp",
                                       "matlab",
                                       "minid",
                                       "modelica",
                                       "modula2",
                                       "mupad",
                                       "nemerle",
                                       "nimrod",
                                       "octave",
                                       "ocaml",
                                       "opa",
                                       "postscript",
                                       "prolog",
                                       "pycon",
                                       "rebol",
                                       "moonscript",
                                       "rbcon",
                                       "splus",
                                       "scala",
                                       "scheme",
                                       "scilab",
                                       "smalltalk",
                                       "tcl",
                                       "vala",
                                       "systemverilog",
                                       "verilog",
                                       "vhdl",
                                       "bash",
                                       "cmake",
                                       "diff",
                                       "ini",
                                       "makefile",
                                       "restructuredtext",
                                       "tex",
                                       "vim",
                                       "bat",
                                       "powershell",
                                       ], name='enum_lang'), index=True)
    author_id = sa.Column('author_id',
                          sa.Integer,
                          sa.ForeignKey('authors.id'),
                          nullable=True)
    changeset_id = sa.Column('changeset_id',
                             sa.Integer,
                             sa.ForeignKey('changesets.id'),
                             nullable=False)  # require at least one version

    author = orm.relationship(Author,
                              backref=orm.backref('snippets', lazy='dynamic'),
                              lazy='joined')
    tags = orm.relationship(Tag,
                            backref=orm.backref('snippets', lazy='dynamic'),
                            secondary=snippets_tags,
                            lazy='joined')
    # the latest changeset
    changeset = orm.relationship(Changeset,
                                 backref=orm.backref('snippet', lazy='joined'),
                                 lazy='joined')
