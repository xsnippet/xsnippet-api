use std::io::Read;

use serde::de::Deserialize;

use rocket::data::{Data, FromData, Outcome, Transform, Transform::*, Transformed};
use rocket::http::{ContentType, Status};
use rocket::outcome::Outcome::*;
use rocket::request::Request;

use crate::errors::ApiError;

/// The default limit for the request size (to prevent DoS attacks). Can be
/// overriden in the config by setting `max_request_size` to a different value
const MAX_REQUEST_SIZE: u64 = 1024 * 1024;
/// The list of supported formats. When changed, the implementation of
/// Input::from_data() must be updated accordingly.
const SUPPORTED_MEDIA_TYPES: [ContentType; 1] = [ContentType::JSON];

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
            match serde_json::from_str(&data) {
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
                ApiError::UnsupportedMediaType(format!(
                    "Support media types: {}",
                    SUPPORTED_MEDIA_TYPES
                        .iter()
                        .map(|v| v.to_string())
                        .collect::<Vec<String>>()
                        .join(",")
                )),
            ))
        }
    }
}
