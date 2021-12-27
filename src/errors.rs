use rocket::http;
use rocket::request::Request;
use rocket::response::{self, Responder, Response};
use rocket::Outcome;
use serde::{ser::SerializeStruct, Serialize, Serializer};

use crate::storage::StorageError;
use crate::web::{NegotiatedContentType, Output};

/// All possible unsuccessful outcomes of an API request.
///
/// Allows to handle application errors in the unified manner:
///
/// 1) all errors are serialized to the requested content type
///    the HTTP status code is set accordingly
///
/// 2) implements conversions from internal errors types (e.g. the errors
///    returned by the Storage trait)
#[derive(Debug)]
pub enum ApiError {
    BadRequest(String),                 // ==> HTTP 400 Bad Request
    Forbidden(String),                  // ==> HTTP 403 Forbidden
    NotFound(String),                   // ==> HTTP 404 Not Found
    NotAcceptable(&'static str),        // ==> HTTP 406 Not Acceptable
    Conflict(String),                   // ==> HTTP 409 Conflict
    UnsupportedMediaType(&'static str), // ==> HTTP 415 Unsupported Media Type
    InternalError(String),              // ==> HTTP 500 Internal Server Error
}

impl ApiError {
    /// Reason why the request failed.
    pub fn reason(&self) -> &str {
        match self {
            ApiError::BadRequest(msg) => msg,
            ApiError::Forbidden(msg) => msg,
            ApiError::NotAcceptable(msg) => msg,
            ApiError::Conflict(msg) => msg,
            ApiError::NotFound(msg) => msg,
            ApiError::InternalError(msg) => msg,
            ApiError::UnsupportedMediaType(msg) => msg,
        }
    }

    /// HTTP status code.
    pub fn status(&self) -> http::Status {
        match self {
            ApiError::BadRequest(_) => http::Status::BadRequest,
            ApiError::Forbidden(_) => http::Status::Forbidden,
            ApiError::NotAcceptable(_) => http::Status::NotAcceptable,
            ApiError::Conflict(_) => http::Status::Conflict,
            ApiError::NotFound(_) => http::Status::NotFound,
            ApiError::UnsupportedMediaType(_) => http::Status::UnsupportedMediaType,
            ApiError::InternalError(_) => http::Status::InternalServerError,
        }
    }
}

impl From<StorageError> for ApiError {
    fn from(value: StorageError) -> Self {
        match value {
            StorageError::Duplicate { id: _ } => ApiError::Conflict(value.to_string()),
            StorageError::NotFound { id: _ } => ApiError::NotFound(value.to_string()),
            _ => ApiError::InternalError(value.to_string()),
        }
    }
}

impl Serialize for ApiError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        let mut s = serializer.serialize_struct("", 1)?;
        s.serialize_field("message", self.reason())?;
        s.end()
    }
}

impl<'r> Responder<'r> for ApiError {
    fn respond_to(self, request: &Request) -> response::Result<'r> {
        if let ApiError::InternalError(_) = self {
            // do not give away any details for internal server errors
            error!("Internal server error: {}", self.reason());
            Response::build()
                .status(http::Status::InternalServerError)
                .ok()
        } else {
            let http_status = self.status();
            debug!("ApiError: {:?}", self);

            match request.guard::<NegotiatedContentType>() {
                // otherwise, present the error in the requested data format if content negotiation
                // has succeeded
                Outcome::Success(_) => Response::build_from(Output(self).respond_to(request)?)
                    .status(http_status)
                    .ok(),
                // or as plain text if content negotiation has failed
                _ => Response::build_from(
                    response::content::Plain(self.reason().to_string()).respond_to(request)?,
                )
                .status(http_status)
                .ok(),
            }
        }
    }
}
