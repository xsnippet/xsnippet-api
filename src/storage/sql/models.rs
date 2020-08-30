use std::convert::From;

use chrono::{DateTime, Utc};

use crate::storage::models::{Changeset, Snippet};

#[derive(Queryable)]
pub struct SnippetRow {
    pub id: i32,
    pub slug: String,
    pub title: Option<String>,
    pub syntax: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Queryable)]
pub struct ChangesetRow {
    pub id: i32,
    pub snippet_id: i32,
    pub version: i32,
    pub content: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Queryable)]
pub struct TagRow {
    pub id: i32,
    pub snippet_id: i32,
    pub value: String,
}

impl From<(SnippetRow, Vec<ChangesetRow>, Vec<TagRow>)> for Snippet {
    fn from(parts: (SnippetRow, Vec<ChangesetRow>, Vec<TagRow>)) -> Self {
        let (snippet_row, changeset_rows, tag_rows) = parts;

        let tags: Vec<String> = tag_rows.into_iter().map(|t| t.value).collect();
        let mut changesets: Vec<Changeset> = changeset_rows
            .into_iter()
            .map(
                |ChangesetRow {
                     id: _,
                     snippet_id: _,
                     version,
                     content,
                     created_at,
                     updated_at,
                 }| {
                    let mut changeset = Changeset::new(version as usize, content);
                    changeset.updated_at = Some(updated_at);
                    changeset.created_at = Some(created_at);

                    changeset
                },
            )
            .collect();
        changesets.sort(); // by version, ascending

        let mut snippet = Snippet::new(snippet_row.title, snippet_row.syntax, changesets, tags);
        snippet.id = snippet_row.slug;
        snippet.created_at = Some(snippet_row.created_at);
        snippet.updated_at = Some(snippet_row.updated_at);

        snippet
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_from() {
        let dt1 = chrono::DateTime::parse_from_rfc3339("2020-08-09T10:39:57+00:00")
            .unwrap()
            .with_timezone(&Utc);
        let dt2 = chrono::DateTime::parse_from_rfc3339("2020-08-10T10:39:57+00:00")
            .unwrap()
            .with_timezone(&Utc);

        let snippet_row = SnippetRow {
            id: 42,
            slug: "spam".to_string(),
            title: Some("Hello".to_string()),
            syntax: Some("python".to_string()),
            created_at: dt1,
            updated_at: dt2,
        };
        let changeset_rows = vec![
            ChangesetRow {
                id: 2,
                snippet_id: 42,
                version: 2,
                content: "print('Hello, World!')".to_string(),
                created_at: dt2,
                updated_at: dt2,
            },
            ChangesetRow {
                id: 1,
                snippet_id: 42,
                version: 1,
                content: "print('Hello!')".to_string(),
                created_at: dt1,
                updated_at: dt1,
            },
        ];
        let tag_rows = vec![
            TagRow {
                id: 1,
                snippet_id: 42,
                value: "spam".to_string(),
            },
            TagRow {
                id: 2,
                snippet_id: 42,
                value: "eggs".to_string(),
            },
        ];

        let actual = Snippet::from((snippet_row, changeset_rows, tag_rows));
        let expected = Snippet {
            id: "spam".to_string(),
            title: Some("Hello".to_string()),
            syntax: Some("python".to_string()),
            changesets: vec![
                Changeset {
                    version: 1,
                    content: "print('Hello!')".to_string(),
                    created_at: Some(dt1),
                    updated_at: Some(dt1),
                },
                Changeset {
                    version: 2,
                    content: "print('Hello, World!')".to_string(),
                    created_at: Some(dt2),
                    updated_at: Some(dt2),
                },
            ],
            tags: vec!["spam".to_string(), "eggs".to_string()],
            created_at: Some(dt1),
            updated_at: Some(dt2),
        };

        assert_eq!(actual, expected);
    }
}
