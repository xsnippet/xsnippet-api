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

class Snippet(Model):
    __table_args__ = (
        sa.Index('ix_snippets_author', 'author_id',
                 postgresql_where=(~sa.sql.column('author_id').is_(None))),
    )

    title = sa.Column('title', sa.String(128), nullable=True, index=True)
    contents = sa.Column('contents', sa.Text(), nullable=False)
    author_id = sa.Column('author_id',
                          sa.Integer,
                          sa.ForeignKey('authors.id'),
                          nullable=True)

    author = orm.relationship(Author,
                              backref=orm.backref('snippets', lazy='dynamic'),
                              lazy='joined')
    tags = orm.relationship(Tag,
                            backref=orm.backref('snippets', lazy='dynamic'),
                            secondary=snippets_tags,
                            lazy='joined')
