mod errors;
mod models;
mod sql;

pub use errors::StorageError;
pub use models::{Changeset, Snippet};
pub use sql::SqlStorage;

/// CRUD interface for storing/loading snippets from a persistent storage.
///
/// Types implementing this trait are required to be both Send and Sync, so
/// that their instances can be safely shared between multiple threads.
pub trait Storage: Send + Sync {
    /// Save the state of the given snippet to the persistent storage.
    fn create(&self, snippet: &Snippet) -> Result<Snippet, StorageError>;

    /// Returns the snippet uniquely identified by a given id (a slug or a
    /// legacy numeric id)
    fn get(&self, id: &str) -> Result<Snippet, StorageError>;

    /// Update the state of the given snippet in the persistent storage
    fn update(&self, snippet: &Snippet) -> Result<Snippet, StorageError>;

    /// Delete the snippet uniquely identified by a given id (a slug or a legacy
    /// numeric id)
    fn delete(&self, id: &str) -> Result<(), StorageError>;
}
