"""Initial schema

Revision ID: 1bf4e4e7b24f
Revises:
Create Date: 2020-07-26 08:46:28.752972

"""

from alembic import op
import sqlalchemy as sa


revision = '1bf4e4e7b24f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    metadata = sa.MetaData()

    sa.Table(
        'snippets', metadata,

        # an internal autoincrementing identifier; only used in foreign keys
        sa.Column('id', sa.Integer, primary_key=True),
        # a short unique snippet identifier visible to users
        sa.Column('slug', sa.String(32), nullable=False),

        sa.Column('title', sa.Text),
        sa.Column('syntax', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),

        # slugs must be unique (this will also automatically create a unique index)
        sa.UniqueConstraint('slug', name='uq_slug'),

        # will be used for pagination; slug guarantees uniqueness of the sorting key
        sa.Index('snippets_created_at_slug', 'created_at', 'slug'),
        sa.Index('snippets_updated_at_slug', 'updated_at', 'slug'),
    )

    sa.Table(
        'changesets', metadata,

        # an internal autoincrementing identifier; only used in foreign keys
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('snippet_id', sa.Integer, nullable=False),

        # numeric index used to determine the ordering of changesets for a given snippet
        sa.Column('version', sa.Integer,
                  server_default=sa.text('0'), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),

        # there can be multiple changesets per snippet; changesets should be
        # deleted when the parent snippet is deleted
        sa.ForeignKeyConstraint(['snippet_id'], ['snippets.id'],
                                ondelete='CASCADE', name='fk_snippet',
                                use_alter=False),
        # each changeset is supposed to have a unique version number
        sa.UniqueConstraint('snippet_id', 'version',
                            name='uq_version'),
        # sanity check: do not allow empty changesets
        sa.CheckConstraint('LENGTH(content) > 0',
                           name='check_not_empty'),
        # sanity check: version numbers are non-negative integers
        sa.CheckConstraint('version >= 0',
                           name='check_non_negative_version')

    )

    # tags could have been associated with snippets as M:M via an auxiliary table,
    # but Diesel only supports child-parent associations, so let's do that instead
    sa.Table(
        'tags', metadata,

        # an internal autoincrementing identifier; only used in foreign keys
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('snippet_id', sa.Integer, nullable=False),

        sa.Column('value', sa.Text, nullable=False),

        # there can be multiple tags per snippet; tags should be deleted when
        # the parent snippet is deleted
        sa.ForeignKeyConstraint(['snippet_id'], ['snippets.id'],
                                ondelete='CASCADE',
                                name='fk_snippet'),

        # do not allow to abuse the tags for storing too much data
        sa.CheckConstraint('LENGTH(value) < 128', name='check_length'),
        # do not allow repeated tags per snippet
        sa.UniqueConstraint('snippet_id', 'value', name='uq_snippet_tag'),
    )

    metadata.create_all(op.get_bind())


def downgrade():
    op.drop_table('tags')
    op.drop_table('changesets')
    op.drop_table('snippets')
