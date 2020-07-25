CREATE TABLE snippets (
    -- an internal autoincrementing identifier used in foreign keys.
    -- Normally not visible publicly, except for the case when it is
    -- used for looking legacy snippets up by id
    id SERIAL PRIMARY KEY,
    -- a short unique snippet identifier visible to users
    slug VARCHAR(32) NOT NULL,

    title TEXT,
    syntax TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- slugs must be unique (this will also automatically create a unique index)
    CONSTRAINT uq_slug UNIQUE (slug)
);


-- will be used for pagination; slug guarantees uniqueness of the sorting key
CREATE INDEX snippets_created_at_slug ON snippets (created_at, slug);
CREATE INDEX snippets_updated_at_slug ON snippets (updated_at, slug);


CREATE TABLE changesets (
    id SERIAL PRIMARY KEY,
    snippet_id INTEGER NOT NULL,

    -- numeric index used to determine the ordering of changesets for a given snippet
    version INTEGER DEFAULT 0 NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- there can be multiple changesets per snippet
    CONSTRAINT fk_snippet FOREIGN KEY (snippet_id) REFERENCES snippets(id),
    -- but each one is supposed to have a unique version number
    CONSTRAINT uq_version UNIQUE (snippet_id, version),
    -- sanity check: do not allow empty changesets
    CONSTRAINT check_not_empty CHECK (LENGTH(content) > 0),
    -- sanity check: version numbers are non-negative integers
    CONSTRAINT check_non_negative_version CHECK (version >= 0)
);


-- tags could have been associated with snippets as M:M via an auxiliary table,
-- but Diesel only supports child-parent associations, so let's do that instead
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    snippet_id INTEGER NOT NULL,

    value TEXT NOT NULL,

    -- there can be multiple tags per snippet
    CONSTRAINT fk_snippet FOREIGN KEY (snippet_id) REFERENCES snippets(id),
    -- do not allow to abuse the tags for storing too much data
    CONSTRAINT check_length CHECK (LENGTH(value) < 128),
    -- do not allow repeated tags per snippet
    CONSTRAINT uq_snippet_tag UNIQUE (snippet_id, value)
);
