// @generated automatically by Diesel CLI.

diesel::table! {
    changesets (id) {
        id -> Int4,
        snippet_id -> Int4,
        version -> Int4,
        content -> Text,
        created_at -> Timestamptz,
        updated_at -> Timestamptz,
    }
}

diesel::table! {
    snippets (id) {
        id -> Int4,
        slug -> Varchar,
        title -> Nullable<Text>,
        syntax -> Nullable<Text>,
        created_at -> Timestamptz,
        updated_at -> Timestamptz,
    }
}

diesel::table! {
    tags (id) {
        id -> Int4,
        snippet_id -> Int4,
        value -> Text,
    }
}

diesel::joinable!(changesets -> snippets (snippet_id));
diesel::joinable!(tags -> snippets (snippet_id));

diesel::allow_tables_to_appear_in_same_query!(changesets, snippets, tags,);
