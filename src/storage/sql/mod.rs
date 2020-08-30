mod models;
mod schema;

use std::convert::From;

use diesel::pg::upsert;
use diesel::prelude::*;
use diesel::r2d2::{ConnectionManager, Pool, PoolError};
use diesel::result::{DatabaseErrorKind, Error::DatabaseError, Error::NotFound};

use super::{errors::StorageError, Snippet, Storage};
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

    fn insert_snippet(&self, conn: &PgConnection, snippet: &Snippet) -> Result<i32, StorageError> {
        let result = diesel::insert_into(snippets::table)
            .values((
                snippets::slug.eq(&snippet.id),
                snippets::title.eq(&snippet.title),
                snippets::syntax.eq(&snippet.syntax),
                snippets::created_at.eq(diesel::dsl::now),
                snippets::updated_at.eq(diesel::dsl::now),
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
        let result = diesel::update(snippets::table.filter(snippets::slug.eq(&snippet.id)))
            .set((
                snippets::title.eq(&snippet.title),
                snippets::syntax.eq(&snippet.syntax),
                snippets::updated_at.eq(diesel::dsl::now),
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
                            changesets::created_at.eq(diesel::dsl::now),
                        )
                    })
                    .collect::<Vec<_>>(),
            )
            .on_conflict((changesets::snippet_id, changesets::version))
            .do_update()
            .set((
                changesets::content.eq(upsert::excluded(changesets::content)),
                changesets::updated_at.eq(diesel::dsl::now),
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
        self.get(&snippet.id)
    }

    fn get(&self, id: &str) -> Result<Snippet, StorageError> {
        let conn = self.pool.get()?;
        conn.transaction::<_, StorageError, _>(|| {
            let result = snippets::table
                .filter(snippets::slug.eq(id))
                .get_result::<models::SnippetRow>(&conn);
            let snippet = match result {
                Ok(snippet) => snippet,
                Err(diesel::NotFound) => return Err(StorageError::NotFound { id: id.to_owned() }),
                Err(e) => return Err(StorageError::from(e)),
            };

            let changesets = changesets::table
                .filter(changesets::snippet_id.eq(snippet.id))
                .get_results::<models::ChangesetRow>(&conn)?;
            let tags = tags::table
                .filter(tags::snippet_id.eq(snippet.id))
                .get_results::<models::TagRow>(&conn)?;

            Ok(Snippet::from((snippet, changesets, tags)))
        })
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

            // reconstruct the created snippet from the state persisted to the database
            // (e.g. so that updated_at fields are correctly populated)
            self.get(&snippet.id)
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
    use super::*;

    use super::super::Changeset;

    /// Compare snippets for equality excluding fields with generated values
    /// (created_at, updated_at)
    fn compare_snippets(expected: &Snippet, actual: &Snippet) {
        assert_eq!(expected.id, actual.id);
        assert_eq!(expected.title, actual.title);
        assert_eq!(expected.syntax, actual.syntax);
        assert_eq!(expected.tags, actual.tags);

        for (expected_changeset, actual_changeset) in
            expected.changesets.iter().zip(actual.changesets.iter())
        {
            assert_eq!(expected_changeset.version, actual_changeset.version);
            assert_eq!(expected_changeset.content, actual_changeset.content);
        }
    }

    #[test]
    fn smoke() {
        // This will be properly covered by the higher level tests, so we just want to
        // do a basic smoke test here. If ROCKET_DATABASE_URL is not set, the
        // test should be skipped.

        let database_url = match std::env::var("ROCKET_DATABASE_URL") {
            Ok(database_url) => database_url,
            Err(_) => return,
        };

        let reference = Snippet::new(
            Some("Hello world".to_string()),
            Some("python".to_string()),
            vec![
                Changeset::new(1, "print('Hello')".to_string()),
                Changeset::new(2, "print('Hello, World!')".to_string()),
            ],
            vec!["spam".to_string(), "eggs".to_string()],
        );
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

        // create a new SqlStorage instance (creates a DB connection pool internally)
        let storage: Box<dyn Storage> = Box::new(
            SqlStorage::new(&database_url).expect("Failed to create a SqlStorage instance"),
        );

        // create a new snippet from the reference value
        let new_snippet = storage
            .create(&reference)
            .expect("Failed to create a snippet");
        compare_snippets(&reference, &new_snippet);

        // retrieve the state of the snippet that was just persisted
        let retrieved_snippet = storage
            .get(&new_snippet.id)
            .expect("Failed to retrieve a snippet");
        // the snippet's state must be exactly the same as the one returned by create()
        // above, including the value of created_at/updated_at fields
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
    }
}
