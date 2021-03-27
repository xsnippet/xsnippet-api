mod models;
mod schema;

use std::convert::From;

use diesel::pg::upsert;
use diesel::prelude::*;
use diesel::r2d2::{ConnectionManager, Pool, PoolError};
use diesel::result::{DatabaseErrorKind, Error::DatabaseError, Error::NotFound};

use super::{errors::StorageError, Direction, ListSnippetsQuery, Snippet, Storage};
use schema::{changesets, snippets, tags};

/// A Storage implementation which persists snippets' data in a SQL database.
pub struct SqlStorage {
    pool: Pool<ConnectionManager<PgConnection>>,
}

impl SqlStorage {
    pub fn new(database_url: &str) -> Result<SqlStorage, StorageError> {
        let manager = ConnectionManager::new(database_url);
        let pool = Pool::builder().build(manager)?;

        Ok(Self { pool })
    }

    fn get_snippet(&self, conn: &PgConnection, id: &str) -> Result<(i32, Snippet), StorageError> {
        let result = snippets::table
            .filter(snippets::slug.eq(id))
            .get_result::<models::SnippetRow>(conn);
        let snippet = match result {
            Ok(snippet) => snippet,
            Err(diesel::NotFound) => return Err(StorageError::NotFound { id: id.to_owned() }),
            Err(e) => return Err(StorageError::from(e)),
        };

        let changesets = changesets::table
            .filter(changesets::snippet_id.eq(snippet.id))
            .get_results::<models::ChangesetRow>(conn)?;
        let tags = tags::table
            .filter(tags::snippet_id.eq(snippet.id))
            .get_results::<models::TagRow>(conn)?;

        Ok((snippet.id, Snippet::from((snippet, changesets, tags))))
    }

    fn insert_snippet(&self, conn: &PgConnection, snippet: &Snippet) -> Result<i32, StorageError> {
        let now = chrono::Utc::now();
        let result = diesel::insert_into(snippets::table)
            .values((
                snippets::slug.eq(&snippet.id),
                snippets::title.eq(&snippet.title),
                snippets::syntax.eq(&snippet.syntax),
                snippets::created_at.eq(snippet.created_at.unwrap_or(now)),
                snippets::updated_at.eq(snippet.updated_at.unwrap_or(now)),
            ))
            .returning(snippets::id)
            .get_result::<i32>(conn);

        match result {
            Ok(snippet_id) => Ok(snippet_id),
            Err(DatabaseError(DatabaseErrorKind::UniqueViolation, _)) => {
                Err(StorageError::Duplicate {
                    id: snippet.id.to_owned(),
                })
            }
            Err(e) => Err(StorageError::from(e)),
        }
    }

    fn update_snippet(&self, conn: &PgConnection, snippet: &Snippet) -> Result<i32, StorageError> {
        let now = chrono::Utc::now();
        let result = diesel::update(snippets::table.filter(snippets::slug.eq(&snippet.id)))
            .set((
                snippets::title.eq(&snippet.title),
                snippets::syntax.eq(&snippet.syntax),
                snippets::updated_at.eq(snippet.updated_at.unwrap_or(now)),
            ))
            .returning(snippets::id)
            .get_result::<i32>(conn);

        match result {
            Ok(snippet_id) => Ok(snippet_id),
            Err(NotFound) => Err(StorageError::NotFound {
                id: snippet.id.to_owned(),
            }),
            Err(e) => Err(StorageError::from(e)),
        }
    }

    fn upsert_changesets(
        &self,
        conn: &PgConnection,
        snippet_id: i32,
        snippet: &Snippet,
    ) -> Result<(), StorageError> {
        let now = chrono::Utc::now();
        diesel::insert_into(changesets::table)
            .values(
                snippet
                    .changesets
                    .iter()
                    .map(|c| {
                        (
                            changesets::snippet_id.eq(snippet_id),
                            changesets::version.eq(c.version as i32),
                            changesets::content.eq(&c.content),
                            changesets::created_at.eq(snippet.created_at.unwrap_or(now)),
                        )
                    })
                    .collect::<Vec<_>>(),
            )
            .on_conflict((changesets::snippet_id, changesets::version))
            .do_update()
            .set((
                changesets::content.eq(upsert::excluded(changesets::content)),
                changesets::updated_at.eq(snippet.updated_at.unwrap_or(now)),
            ))
            .execute(conn)?;

        Ok(())
    }

    fn upsert_tags(
        &self,
        conn: &PgConnection,
        snippet_id: i32,
        snippet: &Snippet,
    ) -> Result<(), StorageError> {
        diesel::insert_into(tags::table)
            .values(
                snippet
                    .tags
                    .iter()
                    .map(|t| (tags::snippet_id.eq(snippet_id), tags::value.eq(t)))
                    .collect::<Vec<_>>(),
            )
            .on_conflict_do_nothing()
            .execute(conn)?;

        Ok(())
    }

    fn trim_removed_tags(
        &self,
        conn: &PgConnection,
        snippet_id: i32,
        snippet: &Snippet,
    ) -> Result<(), StorageError> {
        diesel::delete(
            tags::table.filter(
                tags::snippet_id
                    .eq(snippet_id)
                    .and(tags::value.ne_all(&snippet.tags)),
            ),
        )
        .execute(conn)?;

        Ok(())
    }
}

impl Storage for SqlStorage {
    fn create(&self, snippet: &Snippet) -> Result<Snippet, StorageError> {
        let conn = self.pool.get()?;
        conn.transaction::<_, StorageError, _>(|| {
            // insert the new snippet row first to get the generated primary key
            let snippet_id = self.insert_snippet(&conn, snippet)?;
            // insert the associated changesets
            self.upsert_changesets(&conn, snippet_id, snippet)?;
            // insert the associated tags
            self.upsert_tags(&conn, snippet_id, snippet)?;

            Ok(())
        })?;

        // reconstruct the created snippet from the state persisted to the database
        let (_, created) = self.get_snippet(&conn, &snippet.id)?;
        Ok(created)
    }

    fn list(&self, criteria: ListSnippetsQuery) -> Result<Vec<Snippet>, StorageError> {
        let conn = self.pool.get()?;
        conn.transaction::<_, StorageError, _>(|| {
            let mut query = snippets::table.into_boxed();

            // filters
            if let Some(title) = criteria.title {
                query = query.filter(snippets::title.eq(title));
            }
            if let Some(syntax) = criteria.syntax {
                query = query.filter(snippets::syntax.eq(syntax));
            }
            if let Some(tags) = criteria.tags {
                let snippet_ids = tags::table
                    .select(tags::snippet_id)
                    .filter(tags::value.eq_any(tags));

                query = query.filter(snippets::id.eq_any(snippet_ids));
            }

            // pagination
            if let Some(marker) = criteria.pagination.marker {
                let (marker_internal_id, marker) = self.get_snippet(&conn, &marker)?;
                if let Some(marker_created_at) = marker.created_at {
                    query = match criteria.pagination.direction {
                        Direction::Desc => query
                            .filter(
                                snippets::created_at
                                    .le(marker_created_at)
                                    .and(snippets::id.lt(marker_internal_id)),
                            )
                            .order_by(snippets::created_at.desc())
                            .then_order_by(snippets::id.desc()),
                        Direction::Asc => query
                            .filter(
                                snippets::created_at
                                    .ge(marker_created_at)
                                    .and(snippets::id.gt(marker_internal_id)),
                            )
                            .order_by(snippets::created_at.asc())
                            .then_order_by(snippets::id.asc()),
                    };
                }
            } else {
                query = match criteria.pagination.direction {
                    Direction::Desc => query
                        .order_by(snippets::created_at.desc())
                        .then_order_by(snippets::id.desc()),
                    Direction::Asc => query
                        .order_by(snippets::created_at.asc())
                        .then_order_by(snippets::id.asc()),
                };
            }
            query = query.limit(criteria.pagination.limit as i64);

            let snippets = query.get_results::<models::SnippetRow>(&conn)?;
            let snippet_ids = snippets
                .iter()
                .map(|snippet| snippet.id)
                .collect::<Vec<i32>>();
            let changesets = changesets::table
                .filter(changesets::snippet_id.eq_any(&snippet_ids))
                .get_results::<models::ChangesetRow>(&conn)?;
            let tags = tags::table
                .filter(tags::snippet_id.eq_any(&snippet_ids))
                .get_results::<models::TagRow>(&conn)?;

            Ok(models::combine_rows(snippets, changesets, tags))
        })
    }

    fn get(&self, id: &str) -> Result<Snippet, StorageError> {
        let conn = self.pool.get()?;
        let (_, snippet) = self.get_snippet(&conn, id)?;
        Ok(snippet)
    }

    fn update(&self, snippet: &Snippet) -> Result<Snippet, StorageError> {
        // load the snippet from the db to check if we need to update anything
        let persisted_state = self.get(&snippet.id)?;
        if persisted_state == *snippet {
            // if not, simply return the current state
            Ok(persisted_state)
        } else {
            // otherwise, potentially update the title and the syntax
            let conn = self.pool.get()?;
            conn.transaction::<_, StorageError, _>(|| {
                let snippet_id = self.update_snippet(&conn, snippet)?;
                // insert new changesets and tags
                self.upsert_changesets(&conn, snippet_id, snippet)?;
                self.upsert_tags(&conn, snippet_id, snippet)?;
                // and delete the removed tags
                self.trim_removed_tags(&conn, snippet_id, snippet)?;

                Ok(())
            })?;

            // reconstruct the updated snippet from the state persisted to the database
            // (e.g. so that updated_at fields are correctly populated)
            let (_, updated) = self.get_snippet(&conn, &snippet.id)?;
            Ok(updated)
        }
    }

    fn delete(&self, id: &str) -> Result<(), StorageError> {
        // CASCADE on foreign keys will take care of deleting associated changesets and
        // tags
        let conn = self.pool.get()?;
        let deleted_rows =
            diesel::delete(snippets::table.filter(snippets::slug.eq(id))).execute(&conn)?;
        if deleted_rows == 0 {
            Err(StorageError::NotFound { id: id.to_owned() })
        } else {
            Ok(())
        }
    }
}

// Allow wrapping Diesel errors into StorageError, so that we can distinguish
// them from other variants of the StorageError enum using pattern matching
impl From<diesel::result::Error> for StorageError {
    fn from(error: diesel::result::Error) -> Self {
        StorageError::InternalError(Box::new(error))
    }
}

impl From<diesel::ConnectionError> for StorageError {
    fn from(error: diesel::ConnectionError) -> Self {
        StorageError::InternalError(Box::new(error))
    }
}

impl From<PoolError> for StorageError {
    fn from(error: PoolError) -> Self {
        StorageError::InternalError(Box::new(error))
    }
}

#[cfg(test)]
mod tests {
    use std::collections::HashSet;

    use diesel::r2d2::PooledConnection;

    use super::super::Changeset;
    use super::*;

    /// Compare snippets for equality excluding fields with generated values
    /// (created_at, updated_at)
    fn compare_snippets(expected: &Snippet, actual: &Snippet) {
        assert_eq!(expected.id, actual.id);
        assert_eq!(expected.title, actual.title);
        assert_eq!(expected.syntax, actual.syntax);

        let expected_tags: HashSet<_> = expected.tags.iter().map(|t| t.to_owned()).collect();
        let actual_tags: HashSet<_> = actual.tags.iter().map(|t| t.to_owned()).collect();
        assert_eq!(expected_tags, actual_tags);

        for (expected_changeset, actual_changeset) in
            expected.changesets.iter().zip(actual.changesets.iter())
        {
            assert_eq!(expected_changeset.version, actual_changeset.version);
            assert_eq!(expected_changeset.content, actual_changeset.content);
        }
    }

    /// A fixture that creates a DB connection when ROCKET_DATABASE_URL is set.
    /// The connection is then passed to the given test function. If the url is
    /// not set, the test is skipped.
    ///
    /// The test function is run within a database transaction that is never
    /// committed. This is equivalent to discarding all modifications at the
    /// very end of the test. Because the changes are never committed, they
    /// are never seen by other transactions, so multiple tests can operate
    /// on the same tables in parallel, as if they had exclusive access to
    /// the database.
    fn with_storage<F: FnOnce(Box<dyn Storage>)>(test_function: F) {
        if let Ok(database_url) = std::env::var("ROCKET_DATABASE_URL") {
            let pool = Pool::builder()
                .max_size(1)
                .build(ConnectionManager::new(database_url))
                .expect("Failed to build a db connection pool");

            {
                let conn: PooledConnection<ConnectionManager<PgConnection>> =
                    pool.get().expect("Failed to establish a db connection");

                // start a db transaction that will never be committed. All
                // modifications will be automatically rolled back when the
                // test completes. Any updates will only be seen by this
                // transaction (connection) and no one else
                conn.begin_test_transaction()
                    .expect("Failed to start a test transaction");

                // drop all existing rows in the very beginning of the
                // transaction, so that tests always start with an empty db
                diesel::delete(tags::table)
                    .execute(&conn)
                    .expect("could not delete tags");
                diesel::delete(changesets::table)
                    .execute(&conn)
                    .expect("could not delete changesets");
                diesel::delete(snippets::table)
                    .execute(&conn)
                    .expect("could not delete snippets");

                // return the connection with an open transaction back to the
                // pool. Because the pool has size 1, the very same connection
                // (and thus, the very same open transaction) will be used by
                // the test function below
            }

            test_function(Box::new(SqlStorage { pool }));
        } else {
            error!("ROCKET_DATABASE_URL is not set, skipping the test");
        }
    }

    fn reference_snippets() -> Vec<Snippet> {
        vec![
            Snippet::new(
                Some("Hello world".to_string()),
                Some("python".to_string()),
                vec![
                    Changeset::new(1, "print('Hello')".to_string()),
                    Changeset::new(2, "print('Hello, World!')".to_string()),
                ],
                vec!["spam".to_string(), "eggs".to_string()],
            ),
            Snippet::new(
                Some("Foo".to_string()),
                Some("cpp".to_string()),
                vec![Changeset::new(1, "std::cout << 42.".to_string())],
                vec!["foo".to_string()],
            ),
            Snippet::new(
                Some("Bar".to_string()),
                Some("rust".to_string()),
                vec![Changeset::new(1, "println!(42);".to_string())],
                vec![],
            ),
        ]
    }

    #[test]
    fn crud() {
        // This will be properly covered by higher level tests, so we just
        // want to perform a basic smoke check here.
        with_storage(|storage| {
            let reference = reference_snippets().into_iter().next().unwrap();
            let mut updated_reference = Snippet::new(
                Some("Hello world!".to_string()),
                Some("python".to_string()),
                vec![
                    Changeset::new(1, "print('Hello')".to_string()),
                    Changeset::new(2, "print('Hello, World!')".to_string()),
                    Changeset::new(3, "print('Hello!')".to_string()),
                ],
                vec!["spam".to_string(), "foo".to_string(), "bar".to_string()],
            );
            updated_reference.id = reference.id.clone();

            // create a new snippet from the reference value
            let new_snippet = storage
                .create(&reference)
                .expect("Failed to create a snippet");
            compare_snippets(&reference, &new_snippet);

            // retrieve the state of the snippet that was just persisted
            let retrieved_snippet = storage
                .get(&new_snippet.id)
                .expect("Failed to retrieve a snippet");
            // the snippet's state must be exactly the same as the one returned
            // by create() above, including the value of created_at/updated_at
            // fields
            assert_eq!(new_snippet, retrieved_snippet);

            // try to update the snippet state somehow
            let updated_snippet = storage
                .update(&updated_reference)
                .expect("Failed to update a snippet");
            compare_snippets(&updated_reference, &updated_snippet);

            // finally, delete the snippet
            storage
                .delete(&new_snippet.id)
                .expect("Failed to delete a snippet");

            // and verify that it can't be found in the database anymore
            assert!(match storage.get(&new_snippet.id) {
                Err(StorageError::NotFound { id }) => id == new_snippet.id,
                _ => false,
            });
        });
    }

    #[test]
    fn list() {
        with_storage(|storage| {
            // at this point, listing of snippets should return an empty result
            assert_eq!(
                storage
                    .list(ListSnippetsQuery::default())
                    .expect("Failed to list snippets"),
                vec![]
            );

            // now insert reference snippets and try some queries
            let reference = reference_snippets();
            for snippet in reference.iter() {
                storage.create(snippet).expect("Failed to create a snippet");
            }

            let default_filters = ListSnippetsQuery::default();
            let result = storage
                .list(default_filters)
                .expect("Failed to list snippets");
            for (actual, expected) in result.iter().rev().zip(reference.iter()) {
                compare_snippets(expected, actual);
            }

            let mut by_tag = ListSnippetsQuery::default();
            by_tag.tags = Some(vec!["spam".to_string(), "foo".to_string()]);
            let result = storage.list(by_tag).expect("Failed to list snippets");
            assert_eq!(result.len(), 2);
            for (actual, expected) in result.iter().rev().zip(reference.iter()) {
                compare_snippets(expected, actual);
            }

            let mut by_title = ListSnippetsQuery::default();
            by_title.title = Some("Hello world".to_string());
            let result = storage.list(by_title).expect("Failed to list snippets");
            assert_eq!(result.len(), 1);
            compare_snippets(
                reference
                    .iter()
                    .filter(|s| s.title == Some("Hello world".to_string()))
                    .next()
                    .unwrap(),
                &result[0],
            );

            let mut by_syntax = ListSnippetsQuery::default();
            by_syntax.syntax = Some("rust".to_string());
            let result = storage.list(by_syntax).expect("Failed to list snippets");
            assert_eq!(result.len(), 1);
            compare_snippets(
                reference
                    .iter()
                    .filter(|s| s.syntax == Some("rust".to_string()))
                    .next()
                    .unwrap(),
                &result[0],
            );
        });
    }

    #[test]
    fn pagination() {
        with_storage(|storage| {
            let reference = reference_snippets();
            for snippet in reference.iter() {
                storage.create(snippet).expect("Failed to create a snippet");
            }

            let mut pagination = ListSnippetsQuery::default();
            pagination.pagination.direction = Direction::Asc;
            pagination.pagination.limit = 2;
            let result = storage.list(pagination).expect("Failed to list snippets");
            assert_eq!(result.len(), 2);
            for (actual, expected) in result.iter().zip(reference.iter()) {
                compare_snippets(expected, actual);
            }

            let mut with_marker = ListSnippetsQuery::default();
            with_marker.pagination.direction = Direction::Asc;
            with_marker.pagination.marker = Some(result.last().unwrap().id.clone());
            let result = storage.list(with_marker).expect("Failed to list snippets");
            assert_eq!(result.len(), 1);
            for (actual, expected) in result.iter().skip(1).zip(reference.iter()) {
                compare_snippets(expected, actual);
            }

            let mut with_marker_backward = ListSnippetsQuery::default();
            with_marker_backward.pagination.direction = Direction::Desc;
            with_marker_backward.pagination.limit = 2;
            with_marker_backward.pagination.marker = Some(result.last().unwrap().id.clone());
            let result = storage
                .list(with_marker_backward)
                .expect("Failed to list snippets");
            assert_eq!(result.len(), 2);
            for (actual, expected) in result.iter().skip(1).take(2).zip(reference.iter()) {
                compare_snippets(expected, actual);
            }
        });
    }
}
