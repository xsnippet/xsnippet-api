use std::io::Read;

use serde::de::Deserialize;
use serde::Serialize;

use rocket::http::{Accept, ContentType, HeaderMap, QMediaType, Status};
use rocket::outcome::Outcome::*;
use rocket::request::{self, FromRequest, Request};
use rocket::response::{self, Responder, Response};
use rocket::{
    data::{Data, FromData, Outcome, Transform, Transform::*, Transformed},
    request::FromFormValue,
};
use rocket_contrib::json::Json;

use crate::errors::ApiError;
use crate::storage::Pagination;

/// The default limit for the request size (to prevent DoS attacks). Can be
/// overriden in the config by setting `max_request_size` to a different value
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

impl<'a, T> FromData<'a> for Input<T>
where
    T: Deserialize<'a>,
{
    type Error = ApiError;
    type Owned = String;
    type Borrowed = str;

    fn transform(r: &Request, d: Data) -> Transform<Outcome<Self::Owned, Self::Error>> {
        let size_limit = r
            .limits()
            .get("max_request_size")
            .unwrap_or(MAX_REQUEST_SIZE);

        let mut buf = String::with_capacity(8192);
        match d.open().take(size_limit).read_to_string(&mut buf) {
            Ok(_) => Borrowed(Success(buf)),
            Err(e) => Borrowed(Failure((
                Status::BadRequest,
                ApiError::BadRequest(e.to_string()),
            ))),
        }
    }

    fn from_data(request: &Request, o: Transformed<'a, Self>) -> Outcome<Self, Self::Error> {
        let data = o.borrowed()?;

        let content_type = request.content_type().unwrap_or(&ContentType::JSON);
        if content_type == &ContentType::JSON {
            match serde_json::from_str(data) {
                Ok(v) => Success(Input(v)),
                Err(e) => {
                    if e.is_syntax() {
                        Failure((
                            Status::BadRequest,
                            ApiError::BadRequest("Invalid JSON".to_string()),
                        ))
                    } else {
                        Failure((Status::BadRequest, ApiError::BadRequest(e.to_string())))
                    }
                }
            }
        } else {
            Failure((
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

impl<'a, T: Serialize> Responder<'a> for Output<T> {
    fn respond_to(self, request: &Request) -> response::Result<'a> {
        let Output(value) = self;

        match request.guard::<NegotiatedContentType>() {
            Success(NegotiatedContentType(content_type)) => {
                if content_type == ContentType::JSON {
                    Json(value).respond_to(request)
                } else {
                    // this shouldn't be possible as by this point content negotiation has already
                    // succeded
                    error!("Failed to serialize data to {}", content_type);
                    Err(Status::InternalServerError)
                }
            }
            Failure((_, ApiError::NotAcceptable(msg))) => response::status::Custom(
                Status::NotAcceptable,
                response::content::Plain(msg.to_string()),
            )
            .respond_to(request),
            _ => unreachable!(),
        }
    }
}

/// A Rocket responder that generates response with extra HTTP headers.
pub struct WithHttpHeaders<'h, R>(pub HeaderMap<'h>, pub Option<R>);

impl<'r, R: Responder<'r>> Responder<'r> for WithHttpHeaders<'r, R> {
    fn respond_to(self, request: &Request) -> Result<Response<'r>, Status> {
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

impl FromFormValue<'_> for PaginationLimit {
    type Error = ApiError;

    fn from_form_value(form_value: &rocket::http::RawStr) -> Result<Self, Self::Error> {
        match form_value.parse::<usize>() {
            Ok(limit) => {
                if !(PAGINATION_LIMIT_MIN..=PAGINATION_LIMIT_MAX).contains(&limit) {
                    return Err(ApiError::BadRequest(format!(
                        "Limit must be an integer between {} and {}",
                        PAGINATION_LIMIT_MIN, PAGINATION_LIMIT_MAX
                    )));
                }
                Ok(PaginationLimit(limit))
            }
            Err(message) => Err(ApiError::BadRequest(message.to_string())),
        }
    }
}

/// A guard that analyzes the Accept header of a user request to determine what
/// media type should be used for serializing the response.
///
/// 406 Not Accetable is returned if a user requests an unsupported data format.
pub struct NegotiatedContentType(pub ContentType);

impl Default for NegotiatedContentType {
    fn default() -> Self {
        NegotiatedContentType(PREFERRED_MEDIA_TYPE)
    }
}

impl<'a, 'r> FromRequest<'a, 'r> for NegotiatedContentType {
    type Error = ApiError;

    fn from_request(request: &'a Request<'r>) -> request::Outcome<Self, Self::Error> {
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
            Success(NegotiatedContentType(ContentType(
                Accept::new(supported_types)
                    .preferred()
                    .media_type()
                    .to_owned(),
            )))
        } else {
            // none of the media types specified in the requested are supported. There is
            // nothing we can do other than send a response with an error message
            Failure((
                Status::NotAcceptable,
                ApiError::NotAcceptable(SUPPORTED_MEDIA_TYPES_ERROR),
            ))
        }
    }
}

/// A request guard that only accepts request that specify a specific media type
/// via the Accept header.
pub struct DoNotAcceptAny;

impl<'a, 'r> FromRequest<'a, 'r> for DoNotAcceptAny {
    type Error = ApiError;

    fn from_request(request: &'a Request<'r>) -> request::Outcome<Self, Self::Error> {
        match request.accept() {
            // Accept is passed and it's not */*
            Some(accept) if !accept.preferred().is_any() => Success(DoNotAcceptAny),
            // Accept is not passed, or it's not specific (i.e. */*)
            _ => Forward(()),
        }
    }
}
