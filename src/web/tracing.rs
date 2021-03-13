use rocket::fairing::{Fairing, Info, Kind};
use rocket::request::{self, FromRequest, Request};
use rocket::{Outcome, Response};

/// Unique identifier assigned to a given API request.
pub struct RequestId(pub String);

impl RequestId {
    pub fn new() -> Self {
        RequestId(uuid::Uuid::new_v4().to_hyphenated().to_string())
    }
}

impl Default for RequestId {
    fn default() -> Self {
        RequestId::new()
    }
}

impl<'a, 'r> FromRequest<'a, 'r> for &'a RequestId {
    type Error = ();

    fn from_request(request: &'a Request<'r>) -> request::Outcome<Self, Self::Error> {
        // on first access, generate a new value and store it in the request cache
        Outcome::Success(request.local_cache(RequestId::default))
    }
}

/// Rocket fairing that returns the identifier of the API request in the
/// X-Request-Id response header.
pub struct RequestIdHeader;

impl Fairing for RequestIdHeader {
    fn info(&self) -> Info {
        Info {
            name: "X-Request-Id response header",
            kind: Kind::Response,
        }
    }

    fn on_response(&self, request: &Request, response: &mut Response) {
        if let Some(request_id) = request.guard::<&RequestId>().succeeded() {
            response.set_raw_header("X-Request-Id", request_id.0.clone());
        } else {
            eprintln!("Failed to generate a request id");
        }
    }
}
