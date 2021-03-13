mod jwt;

use std::{error, fmt};

use rocket::http::Status;
use rocket::outcome::Outcome;
use rocket::request::{self, FromRequest, Request};
use serde::Deserialize;

pub use jwt::JwtValidator;

#[derive(Debug, PartialEq, Deserialize)]
pub enum Permission {
    /// Allows superusers to perform any actions.
    #[serde(rename(deserialize = "admin"))]
    Admin,
}

#[derive(Debug, PartialEq)]
pub enum User {
    /// Authenticated user. Can create, retrieve, update, and delete private
    /// snippets. May have additional permissions (e.g. if this is an admin
    /// user).
    Authenticated {
        name: String,
        permissions: Vec<Permission>,
    },

    /// Anonymous user. Can create and retrieve publicly available snippets.
    Guest,
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

impl<'a, 'r> FromRequest<'a, 'r> for BearerAuth {
    type Error = Error;

    fn from_request(request: &'a Request<'r>) -> request::Outcome<Self, Self::Error> {
        match request.headers().get_one("Authorization") {
            Some(value) => match value.split_once(' ') {
                Some(("Bearer", token)) => {
                    if let Some(validator) = request
                        .guard::<rocket::State<Box<dyn AuthValidator>>>()
                        .succeeded()
                    {
                        match validator.validate(token) {
                            Ok(user) => Outcome::Success(BearerAuth(user)),
                            Err(err) => {
                                debug!("{}", err);

                                match err {
                                    Error::Input(_) => Outcome::Failure((Status::BadRequest, err)),
                                    _ => Outcome::Failure((Status::Forbidden, err)),
                                }
                            }
                        }
                    } else {
                        let err =
                            Error::Configuration("Token validator is not configured".to_string());
                        error!("{}", err);

                        Outcome::Failure((Status::ServiceUnavailable, err))
                    }
                }
                _ => {
                    let err = Error::Input(format!("Invalid Authorization header: {}", value));
                    debug!("{}", err);

                    Outcome::Failure((Status::BadRequest, err))
                }
            },
            None => Outcome::Success(BearerAuth(User::Guest)),
        }
    }
}
