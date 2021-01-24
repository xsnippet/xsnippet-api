use std::iter;

use rand::Rng;
use serde::Serialize;

use crate::storage::DateTime;

const DEFAULT_LIMIT_SIZE: usize = 20;
const DEFAULT_SLUG_LENGTH: usize = 8;

/// A code snippet
#[derive(Debug, Default, Eq, PartialEq, Serialize)]
pub struct Snippet {
    /// Slug that uniquely identifies the snippet
    pub id: String,
    /// Snippet title. None means that the title was not specified at snippet
    /// creation time
    pub title: Option<String>,
    /// Snippet syntax. None means that the syntax was not specified at snippet
    /// creation time
    pub syntax: Option<String>,
    /// List of revisions. The snippet content is the content of the most recent
    /// revision. Revisions are sorted by the version number in the
    /// ascending order.
    pub changesets: Vec<Changeset>,
    /// List of tags attached to the snippet
    pub tags: Vec<String>,
    /// Timestamp of when the snippet was created
    pub created_at: Option<DateTime>,
    /// Timestamp of when the snippet was last modified. Defaults to creation
    /// time
    pub updated_at: Option<DateTime>,
}

impl Snippet {
    /// Create a new Snippet.
    pub fn new(
        title: Option<String>,
        syntax: Option<String>,
        changesets: Vec<Changeset>,
        tags: Vec<String>,
    ) -> Self {
        Snippet {
            id: Snippet::random_id(DEFAULT_SLUG_LENGTH),
            title,
            syntax,
            changesets,
            tags,
            ..Default::default()
        }
    }

    /// Generate a random unique snippet identifier (slug).
    pub fn random_id(length: usize) -> String {
        let mut rng = rand::thread_rng();
        iter::repeat_with(|| rng.sample(rand::distributions::Alphanumeric))
            .take(length)
            .collect()
    }
}

#[derive(Debug)]
pub enum Direction {
    /// From older to newer snippets.
    #[allow(dead_code)]
    Asc,
    /// From newer to older snippets.
    Desc,
}

#[derive(Debug)]
pub struct Pagination {
    /// Pagination direction.
    pub direction: Direction,
    /// The maximum number of snippets per page.
    pub limit: usize,
    /// The id (slug) of the last snippet on the previous page. Used to identify
    /// the first snippet on the next page. If not set, pagination starts
    /// from the newest or the oldest snippet, depending on the chosen
    /// diretion.
    pub marker: Option<String>,
}

impl Default for Pagination {
    fn default() -> Self {
        Pagination {
            direction: Direction::Desc,
            limit: DEFAULT_LIMIT_SIZE,
            marker: None,
        }
    }
}

#[derive(Debug, Default)]
pub struct ListSnippetsQuery {
    /// If set, only the snippets with the specified title will be returned.
    pub title: Option<String>,
    /// If set, only the snippets with the specified syntax will be returned.
    pub syntax: Option<String>,
    /// If set, only the snippets that have *one of* the specified tags attached
    /// will be returned.
    pub tags: Option<Vec<String>>,
    /// Pagination parameters.
    pub pagination: Pagination,
}

/// A particular snippet revision
#[derive(Debug, Default, Eq, Ord, PartialEq, PartialOrd, Serialize)]
pub struct Changeset {
    /// Changeset index. Version numbers start from 0 and are incremented by 1
    pub version: usize,
    /// Changeset content
    pub content: String,
    /// Timestamp of when the changeset was created
    pub created_at: Option<DateTime>,
    /// Timestamp of when the changeset was last modified. Defaults to creation
    /// time
    pub updated_at: Option<DateTime>,
}

impl Changeset {
    /// Create a new Changeset.
    pub fn new(version: usize, content: String) -> Self {
        Changeset {
            version,
            content,
            ..Default::default()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_snippet() {
        let snippet = Snippet::default();

        assert_eq!(snippet.id, "");
        assert_eq!(snippet.title, None);
        assert_eq!(snippet.syntax, None);
        assert_eq!(snippet.changesets, vec![] as Vec<Changeset>);
        assert_eq!(snippet.tags, vec![] as Vec<String>);
        assert_eq!(snippet.created_at, None);
        assert_eq!(snippet.updated_at, None);
    }

    #[test]
    fn test_new_snippet() {
        let snippet = Snippet::new(
            Some("Hello".to_string()),
            Some("python".to_string()),
            vec![Changeset::new(0, "print('Hello, World!')".to_string())],
            vec!["#python".to_string()],
        );

        assert_eq!(snippet.id.len(), DEFAULT_SLUG_LENGTH);
        assert_eq!(snippet.title, Some("Hello".to_string()));
        assert_eq!(snippet.syntax, Some("python".to_string()));
        assert_eq!(
            snippet.changesets,
            vec![Changeset::new(0, "print('Hello, World!')".to_string())]
        );
        assert_eq!(snippet.tags, vec!["#python".to_string()]);
        assert_eq!(snippet.created_at, None);
        assert_eq!(snippet.updated_at, None);
    }

    #[test]
    fn test_snippet_equality() {
        let reference = Snippet {
            id: "spam".to_string(),
            title: Some("Hello".to_string()),
            syntax: Some("python".to_string()),
            changesets: vec![Changeset::new(0, "print('Hello, World!')".to_string())],
            tags: vec!["#python".to_string()],
            created_at: None,
            updated_at: None,
        };
        let equal = Snippet {
            id: "spam".to_string(),
            title: Some("Hello".to_string()),
            syntax: Some("python".to_string()),
            changesets: vec![Changeset::new(0, "print('Hello, World!')".to_string())],
            tags: vec!["#python".to_string()],
            created_at: None,
            updated_at: None,
        };
        let different_title = Snippet {
            id: "spam".to_string(),
            title: None,
            syntax: Some("python".to_string()),
            changesets: vec![Changeset::new(0, "print('Hello, World!')".to_string())],
            tags: vec!["#python".to_string()],
            created_at: None,
            updated_at: None,
        };
        let different_syntax = Snippet {
            id: "spam".to_string(),
            title: Some("Hello".to_string()),
            syntax: None,
            changesets: vec![Changeset::new(0, "print('Hello, World!')".to_string())],
            tags: vec!["#python".to_string()],
            created_at: None,
            updated_at: None,
        };
        let different_changesets = Snippet {
            id: "spam".to_string(),
            title: Some("Hello".to_string()),
            syntax: None,
            changesets: vec![Changeset::new(1, "print('Hello, World!')".to_string())],
            tags: vec!["#python".to_string()],
            created_at: None,
            updated_at: None,
        };
        let different_tags = Snippet {
            id: "spam".to_string(),
            title: Some("Hello".to_string()),
            syntax: Some("python".to_string()),
            changesets: vec![Changeset::new(0, "print('Hello, World!')".to_string())],
            tags: vec![],
            created_at: None,
            updated_at: None,
        };

        assert_eq!(reference, equal);
        assert_eq!(equal, reference);

        assert_ne!(reference, different_title);
        assert_ne!(reference, different_syntax);
        assert_ne!(reference, different_changesets);
        assert_ne!(reference, different_tags);
        assert_ne!(different_title, reference);
        assert_ne!(different_syntax, reference);
        assert_ne!(different_changesets, reference);
        assert_ne!(different_tags, reference);
    }

    #[test]
    fn test_random_id() {
        let iterations = 10000;
        let length = 7;

        // verify that ids are sufficiently random
        let generated_ids: std::collections::HashSet<_> =
            std::iter::repeat_with(|| Snippet::random_id(length))
                .take(iterations)
                .collect();
        assert_eq!(generated_ids.len(), iterations);

        // verify that ids are generated with the specified length and only
        // contain characters from the 'a'-'z', 'A'-'Z', '0'-'9' ranges
        for id in generated_ids.iter() {
            assert_eq!(id.len(), length);
            assert!(
                id.chars().all(|c| c.is_ascii_alphanumeric()),
                id.to_string()
            );
        }
    }

    #[test]
    fn test_default_changeset() {
        let changeset = Changeset::default();

        assert_eq!(changeset.version, 0);
        assert_eq!(changeset.content, "");
        assert_eq!(changeset.created_at, None);
        assert_eq!(changeset.updated_at, None);
    }

    #[test]
    fn test_new_changeset() {
        let changeset = Changeset::new(42, "print('Hello, World!')".to_string());

        assert_eq!(changeset.version, 42);
        assert_eq!(changeset.content, "print('Hello, World!')".to_string());
        assert_eq!(changeset.created_at, None);
        assert_eq!(changeset.updated_at, None);
    }

    #[test]
    fn test_changeset_ordering() {
        let changeset1 = Changeset::new(42, "print('Hello!')".to_string());
        let changeset2 = Changeset::new(43, "print('Hello, World!')".to_string());

        assert!(changeset1 < changeset2);
        assert!(changeset1 <= changeset2);
        assert!(changeset2 > changeset1);
        assert!(changeset2 >= changeset1);
    }

    #[test]
    fn test_changeset_equality() {
        let reference = Changeset::new(42, "print('Hello!')".to_string());
        let equal = Changeset::new(42, "print('Hello!')".to_string());
        let different_version = Changeset::new(43, "print('Hello!')".to_string());
        let different_content = Changeset::new(42, "print('Hello, World!')".to_string());

        assert_eq!(reference, equal);
        assert_eq!(equal, reference);

        assert_ne!(reference, different_version);
        assert_ne!(reference, different_content);
        assert_ne!(different_version, reference);
        assert_ne!(different_content, reference);
    }

    #[test]
    fn test_serialization() {
        let dt = chrono::DateTime::parse_from_rfc3339("2020-08-09T10:39:57+00:00")
            .unwrap()
            .with_timezone(&chrono::Utc);
        let reference = Snippet {
            id: "spam".to_string(),
            title: Some("Hello".to_string()),
            syntax: Some("python".to_string()),
            changesets: vec![Changeset::new(0, "print('Hello, World!')".to_string())],
            tags: vec!["foo".to_string(), "bar".to_string()],
            created_at: Some(dt.into()),
            updated_at: None,
        };

        let expected = "{\
            \"id\":\"spam\",\
            \"title\":\"Hello\",\
            \"syntax\":\"python\",\
            \"changesets\":[\
                {\
                    \"version\":0,\
                    \"content\":\"print(\'Hello, World!\')\",\
                    \"created_at\":null,\
                    \"updated_at\":null\
                }\
            ],\
            \"tags\":[\"foo\",\"bar\"],\
            \"created_at\":\"2020-08-09T10:39:57+00:00\",\
            \"updated_at\":null\
        }";
        let actual = serde_json::to_string(&reference).expect("failed to serialize snippet");
        assert_eq!(actual, expected);
    }
}
