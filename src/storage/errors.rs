use std::error;
use std::fmt;

/// All errors that can be returned by the storage layer wrapped into a single
/// enum type for convenience.
#[derive(Debug)]
pub enum StorageError {
    /// Snippet with this id already exists in the database
    Duplicate { id: String },
    /// Snippet with this id can't be found
    NotFound { id: String },
    /// All other errors that can't be handled by the storage layer
    InternalError(Box<dyn error::Error + Send>),
}

impl fmt::Display for StorageError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            StorageError::Duplicate { id } => write!(f, "Snippet with id `{}` already exists", id),
            StorageError::NotFound { id } => write!(f, "Snippet with id `{}` is not found", id),
            StorageError::InternalError(e) => write!(f, "Internal error: `{}`", e),
        }
    }
}

// this is not strictly required, but allows for wrapping a StorageError
// instance into a Box<dyn Error> if needed. Error's only requirement is for
// a type to implement Debug + Display
impl error::Error for StorageError {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_display() {
        assert_eq!(
            "Snippet with id `spam` already exists",
            format!(
                "{}",
                StorageError::Duplicate {
                    id: "spam".to_string()
                }
            )
        );

        assert_eq!(
            "Snippet with id `eggs` is not found",
            format!(
                "{}",
                StorageError::NotFound {
                    id: "eggs".to_string()
                }
            )
        );

        let error = "foo".parse::<f32>().err().unwrap();
        assert_eq!(
            "Internal error: `invalid float literal`",
            format!("{}", StorageError::InternalError(Box::new(error)))
        );
    }
}
