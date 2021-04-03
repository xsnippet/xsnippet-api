use std::convert::From;

use rocket::http;
use rocket::request::Request;
use rocket::response::{self, Responder, Response};
use serde::{ser::SerializeStruct, Serialize, Serializer};

use crate::storage::StorageError;
use crate::web::Output;

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
    NotFound(String),                   // ==> HTTP 404 Not Found
    NotAcceptable(&'static str),        // ==> HTTP 406 Not Acceptable
    UnsupportedMediaType(&'static str), // ==> HTTP 415 Unsupported Media Type
    InternalError(String),              // ==> HTTP 500 Internal Server Error
}

impl ApiError {
    /// Reason why the request failed.
    pub fn reason(&self) -> &str {
        match self {
            ApiError::BadRequest(msg) => &msg,
            ApiError::NotAcceptable(msg) => &msg,
            ApiError::NotFound(msg) => &msg,
            ApiError::InternalError(msg) => &msg,
            ApiError::UnsupportedMediaType(msg) => &msg,
        }
    }

    /// HTTP status code.
    pub fn status(&self) -> http::Status {
        match self {
            ApiError::BadRequest(_) => http::Status::BadRequest,
            ApiError::NotAcceptable(_) => http::Status::NotAcceptable,
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
    fn respond_to(self, request: &Request) -> response::Result<'r> {
        if let ApiError::InternalError(_) = self {
            // do not give away any details for internal server errors
            error!("Internal server error: {}", self.reason());
            Response::build()
                .status(http::Status::InternalServerError)
                .ok()
        } else {
            // otherwise, present the error in the requested data format
            let http_status = self.status();
            debug!("ApiError: {:?}", self);
            Response::build_from(Output(self).respond_to(request)?)
                .status(http_status)
                .ok()
        }
    }
}