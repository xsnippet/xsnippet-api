use std::convert::From;
use std::io::Cursor;

use rocket::http;
use rocket::request::Request;
use rocket::response::{self, Responder, Response};
use serde::{ser::SerializeStruct, Serialize, Serializer};

use crate::storage::StorageError;

/// All possible unsuccessful outcomes of an API request.
///
/// Allows to handle application errors in the unified manner:
///
/// 1) all errors are serialized to JSON messages like {"message": "..."};
///    the HTTP status code is set accordingly
///
/// 2) implements conversions from internal errors types (e.g. the errors
///    returned by the Storage trait)
#[derive(Debug)]
pub enum ApiError {
    BadRequest(String),
    NotFound(String),
    InternalError(String),
    UnsupportedMediaType(String),
}

impl ApiError {
    /// Reason why the request failed.
    pub fn reason(&self) -> &str {
        match self {
            ApiError::BadRequest(msg) => &msg,
            ApiError::NotFound(msg) => &msg,
            ApiError::InternalError(msg) => &msg,
            ApiError::UnsupportedMediaType(msg) => &msg,
        }
    }

    /// HTTP status code.
    pub fn status(&self) -> http::Status {
        match self {
            ApiError::BadRequest(_) => http::Status::BadRequest,
            ApiError::NotFound(_) => http::Status::NotFound,
            ApiError::UnsupportedMediaType(_) => http::Status::UnsupportedMediaType,
            ApiError::InternalError(_) => http::Status::InternalServerError,
        }
    }
}

impl From<StorageError> for ApiError {
    fn from(value: StorageError) -> Self {
        match value {
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
    fn respond_to(self, _request: &Request) -> response::Result<'r> {
        let mut response = Response::build();

        if let ApiError::InternalError(_) = self {
            // do not give away any details for internal server errors
            // TODO: integrate with Rocket contextual logging when 0.5 is released
            eprintln!("Internal server error: {}", self.reason());
            response.status(http::Status::InternalServerError).ok()
        } else {
            // otherwise, present the error as JSON and set the status code accordingly
            response
                .status(self.status())
                .header(http::ContentType::JSON)
                .sized_body(Cursor::new(json!(self).to_string()))
                .ok()
        }
    }
}
