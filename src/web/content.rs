use serde::de::DeserializeOwned;
use serde::Serialize;

use rocket::data::{self, Data, FromData, ToByteUnit};
use rocket::form::{self, FromFormField, ValueField};
use rocket::http::{Accept, ContentType, HeaderMap, QMediaType, Status};
use rocket::outcome::Outcome::*;
use rocket::request::{self, FromRequest, Request};
use rocket::response::{self, Responder, Response};
use rocket::serde::json::Json;

use crate::errors::ApiError;
use crate::storage::Pagination;

/// The default limit for the request size (to prevent DoS attacks). Can be
/// overridden in the config by setting `max_request_size` to a different value
const MAX_REQUEST_SIZE: u64 = 1024 * 1024;
/// The list of supported formats. When changed, the implementation of
/// Input::from_data() must be updated accordingly.
const SUPPORTED_MEDIA_TYPES: [ContentType; 1] = [ContentType::JSON];
const SUPPORTED_MEDIA_TYPES_ERROR: &str = "Support media types: application/json";
const PREFERRED_MEDIA_TYPE: ContentType = ContentType::JSON;
// Pagination limit boundaries. Values outside of the boundary are not allowed
// and will fail the request.
const PAGINATION_LIMIT_MIN: usize = 1;
const PAGINATION_LIMIT_MAX: usize = 20;

/// A wrapper struct that implements [`FromData`], allowing to accept data
/// serialized into different formats. The value of the Content-Type request
/// header is used to choose the deserializer. The default (and the only
/// supported at the moment) content type is application/json.
///
/// 400 Bad Request is returned if data deserialization fails for any reason.
/// 415 Unsupported Media Type is returned if a client has requested an
/// unsupported format.
///
/// All errors are reported as ApiError.
#[derive(Debug)]
pub struct Input<T>(pub T);

#[rocket::async_trait]
impl<'r, T> FromData<'r> for Input<T>
where
    T: DeserializeOwned,
{
    type Error = ApiError;

    async fn from_data(request: &'r Request<'_>, data: Data<'r>) -> data::Outcome<'r, Self> {
        let size_limit = request
            .limits()
            .get("max_request_size")
            .unwrap_or_else(|| MAX_REQUEST_SIZE.bytes());

        let input = match data.open(size_limit).into_string().await {
            Ok(string) if string.is_complete() => string.into_inner(),
            Ok(_) => {
                return Error((
                    Status::PayloadTooLarge,
                    ApiError::BadRequest("Payload too large".to_string()),
                ))
            }
            Err(e) => {
                return Error((
                    Status::InternalServerError,
                    ApiError::InternalError(e.to_string()),
                ))
            }
        };

        let content_type = request
            .content_type()
            .cloned()
            .unwrap_or(PREFERRED_MEDIA_TYPE);
        if content_type == ContentType::JSON {
            match serde_json::from_str(&input) {
                Ok(v) => Success(Input(v)),
                Err(e) => {
                    if e.is_syntax() {
                        Error((
                            Status::BadRequest,
                            ApiError::BadRequest("Invalid JSON".to_string()),
                        ))
                    } else {
                        Error((Status::BadRequest, ApiError::BadRequest(e.to_string())))
                    }
                }
            }
        } else {
            Error((
                Status::UnsupportedMediaType,
                ApiError::UnsupportedMediaType(SUPPORTED_MEDIA_TYPES_ERROR),
            ))
        }
    }
}

/// A wrapper struct that implements [`Responder`], allowing to serialize the
/// response to the format negotiated with the client via the provided request
/// headers.
pub struct Output<T>(pub T);

impl<'r, 'o: 'r, T: Serialize> Responder<'r, 'o> for Output<T> {
    fn respond_to(self, request: &'r Request) -> response::Result<'o> {
        let Output(value) = self;
        let NegotiatedContentType(content_type) =
            request.local_cache(|| /* default */ NegotiatedContentType(PREFERRED_MEDIA_TYPE));

        if content_type == &ContentType::JSON {
            Json(value).respond_to(request)
        } else {
            // this shouldn't be possible as by this point content negotiation has already
            // succeeded
            error!("Failed to serialize data to {}", content_type);
            Err(Status::InternalServerError)
        }
    }
}

/// A Rocket responder that generates response with extra HTTP headers.
pub struct WithHttpHeaders<'h, R>(pub HeaderMap<'h>, pub Option<R>);

impl<'r, 'o: 'r, R: Responder<'r, 'o>> Responder<'r, 'o> for WithHttpHeaders<'o, R> {
    fn respond_to(self, request: &'r Request<'_>) -> response::Result<'o> {
        let mut build = Response::build();

        if let Some(responder) = self.1 {
            build.merge(responder.respond_to(request)?);
        }

        for header in self.0.into_iter() {
            build.header(header);
        }

        build.ok()
    }
}

/// A guard that implements extra validation for pagination's 'limit' value.
/// Essentially ensures it lies within an allowed range.
pub struct PaginationLimit(pub usize);

impl Default for PaginationLimit {
    fn default() -> Self {
        PaginationLimit(Pagination::DEFAULT_LIMIT_SIZE)
    }
}

#[rocket::async_trait]
impl FromFormField<'_> for PaginationLimit {
    fn default() -> Option<Self> {
        Some(Default::default())
    }

    fn from_value(field: ValueField<'_>) -> form::Result<'_, Self> {
        match field.value.parse::<usize>() {
            Ok(limit) => {
                if !(PAGINATION_LIMIT_MIN..=PAGINATION_LIMIT_MAX).contains(&limit) {
                    return Err(form::Error::validation(format!(
                        "Limit must be an integer between {} and {}",
                        PAGINATION_LIMIT_MIN, PAGINATION_LIMIT_MAX
                    ))
                    .into());
                }
                Ok(PaginationLimit(limit))
            }
            Err(e) => {
                Err(form::Error::validation(format!("Limit must be an integer: {}", e)).into())
            }
        }
    }
}

/// A guard that analyzes the Accept header of a user request to determine what
/// media type should be used for serializing the response.
///
/// 406 Not Acceptable is returned if a user requests an unsupported data format.
pub struct NegotiatedContentType(pub ContentType);

impl Default for NegotiatedContentType {
    fn default() -> Self {
        NegotiatedContentType(PREFERRED_MEDIA_TYPE)
    }
}

#[rocket::async_trait]
impl<'r> FromRequest<'r> for &'r NegotiatedContentType {
    type Error = ApiError;

    async fn from_request(request: &'r Request<'_>) -> request::Outcome<Self, Self::Error> {
        // go through all requested media types in the request and check which of them
        // we support
        let mut supported_types = vec![];
        for requested_type in request.accept().unwrap_or(&Accept::Any).iter() {
            if let Some(supported_type) =
                SUPPORTED_MEDIA_TYPES
                    .iter()
                    .find_map(|ContentType(supported_type)| {
                        // if it's an exact match, copy the requested type with
                        // the specified priority
                        if requested_type.media_type() == supported_type {
                            Some(requested_type.clone())
                        // otherwise, if the request allows for any media type,
                        // copy the first type that we support
                        } else if requested_type.is_any() {
                            Some(QMediaType(supported_type.clone(), None))
                        // this media type is not supported. We'll try another
                        // one on the next iteration of the loop
                        } else {
                            None
                        }
                    })
            {
                supported_types.push(supported_type);
            }
        }

        if !supported_types.is_empty() {
            // pick the media type with the highest priority among the ones that we support
            let selected = NegotiatedContentType(ContentType(
                Accept::new(supported_types)
                    .preferred()
                    .media_type()
                    .to_owned(),
            ));

            // caching is only required to give [`Output`] access to the negotiated content type,
            // as it can no longer call the [`NegotiatedContentType`] guard directly ([`Responder`]
            // is a sync trait, while [`NegotiatedContentType`], as all request guards, is an async one)
            Success(request.local_cache(|| selected))
        } else {
            // none of the media types specified in the requested are supported. There is
            // nothing we can do other than send a response with an error message
            Error((
                Status::NotAcceptable,
                ApiError::NotAcceptable(SUPPORTED_MEDIA_TYPES_ERROR),
            ))
        }
    }
}

/// A request guard that only accepts request that specify a specific media type
/// via the Accept header.
pub struct DoNotAcceptAny;

#[rocket::async_trait]
impl<'r> FromRequest<'r> for DoNotAcceptAny {
    type Error = ApiError;

    async fn from_request(request: &'r Request<'_>) -> request::Outcome<Self, Self::Error> {
        match request.accept() {
            // Accept is passed and it's not */*
            Some(accept) if !accept.preferred().is_any() => Success(DoNotAcceptAny),
            // Accept is not passed, or it's not specific (i.e. */*)
            _ => Forward(Status::BadRequest),
        }
    }
}
