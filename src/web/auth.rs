mod jwt;

use std::{error, fmt};

use rocket::http::Status;
use rocket::request::{self, FromRequest, Outcome, Request};
use serde::Deserialize;

pub use jwt::JwtValidator;

#[derive(Debug, PartialEq, Eq, Deserialize)]
pub enum Permission {
    /// Allows users to import snippets (i.e. to create new snippets and set
    /// the values of some protected Snippet fields like `id` or `created_at`).
    #[serde(rename(deserialize = "import"))]
    Import,
}

#[derive(Debug, PartialEq, Eq)]
pub enum User {
    /// Authenticated user. Can create, retrieve, update, and delete private
    /// snippets. May have additional permissions.
    Authenticated {
        name: String,
        permissions: Vec<Permission>,
    },

    /// Anonymous user. Can create and retrieve publicly available snippets.
    Guest,
}

impl User {
    /// Returns true if the user is allowed to import snippets (i.e. set values
    /// of the fields that normally are automatically generated, e.g. `id`
    /// or `created_at`).
    pub fn can_import_snippets(&self) -> bool {
        if let User::Authenticated { permissions, .. } = self {
            permissions.contains(&Permission::Import)
        } else {
            false
        }
    }
}

#[derive(Debug)]
pub enum Error {
    /// Server is misconfigured or the critical dependency is unavailable.
    Configuration(String),

    /// User input is malformed or incomplete.
    Input(String),

    /// Token validation failed (e.g. because it has expired or the signature is
    /// incorrect).
    Validation(String),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:?}", *self)
    }
}
impl error::Error for Error {}

pub type Result<T> = std::result::Result<T, Error>;

/// A common interface for validation of user tokens.
pub trait AuthValidator: Send + Sync {
    /// Validate a given token value and determine permissions of the user.
    fn validate(&self, token: &str) -> Result<User>;
}

/// A guard that performs authorization using the Bearer token passed in the
/// request headers. Expects the token validator to be configured as
/// rocket::State<Box<dyn Validator>>.
pub struct BearerAuth(pub User);

#[rocket::async_trait]
impl<'r> FromRequest<'r> for BearerAuth {
    type Error = Error;

    async fn from_request(request: &'r Request<'_>) -> request::Outcome<Self, Self::Error> {
        match request.headers().get_one("Authorization") {
            Some(value) => match value.split_once(' ') {
                Some(("Bearer", token)) => {
                    if let Some(validator) = request
                        .guard::<&rocket::State<Box<dyn AuthValidator>>>()
                        .await
                        .succeeded()
                    {
                        match validator.validate(token) {
                            Ok(user) => Outcome::Success(BearerAuth(user)),
                            Err(err) => {
                                debug!("{}", err);

                                match err {
                                    Error::Input(_) => Outcome::Error((Status::BadRequest, err)),
                                    _ => Outcome::Error((Status::Forbidden, err)),
                                }
                            }
                        }
                    } else {
                        let err =
                            Error::Configuration("Token validator is not configured".to_string());
                        error!("{}", err);

                        Outcome::Error((Status::ServiceUnavailable, err))
                    }
                }
                _ => {
                    let err = Error::Input(format!("Invalid Authorization header: {}", value));
                    debug!("{}", err);

                    Outcome::Error((Status::BadRequest, err))
                }
            },
            None => Outcome::Success(BearerAuth(User::Guest)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn can_import_snippets() {
        let guest = User::Guest;
        let user = User::Authenticated {
            name: String::from("user"),
            permissions: vec![],
        };
        let importer = User::Authenticated {
            name: String::from("importer"),
            permissions: vec![Permission::Import],
        };

        assert!(!guest.can_import_snippets());
        assert!(!user.can_import_snippets());
        assert!(importer.can_import_snippets());
    }
}
