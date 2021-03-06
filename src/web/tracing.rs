use std::cell::RefCell;

use rocket::fairing::{Fairing, Info, Kind};
use rocket::request::{self, FromRequest, Request};
use rocket::{Data, Outcome, Response};
use tracing::field::Empty;
use tracing::span::EnteredSpan;

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
            error!("Failed to generate a request id");
        }
    }
}

/// Rocket fairing that creates and destroys a request `span`.
///
/// tracing framework uses a notion of `spans` to store contextual information
/// alongside log events. For web applications a typical span would be a single
/// HTTP request, which has a beginning and end time, unique request identifier,
/// etc.
///
/// A natural point of integration with Rocket is a fairing, which allows us to
/// execute some code before and after each HTTP request, which is exactly what
/// we need for determining the boundaries of a request span.
pub struct RequestSpan;

// It is extremely annoying that we need to resort to storing the span guard in
// a thread local instead of the Rocket Request local cache, but those two have
// incompatible requirements:
//
//  * EnteredSpan is marked as !Send, so that it's not possible to move it
//    between threads, as that would produce incorrect traces
//
//  * Request::local_cache() requires the type to be Send, even though the
//    values are not actually transferred between threads
//
// Using a thread-local is fine, because both on_request()/on_response() and the
// actual request handler are executed in the same thread.
thread_local!(static REQUEST_SPAN: RefCell<Option<EnteredSpan>> = RefCell::new(None));

impl Fairing for RequestSpan {
    fn info(&self) -> Info {
        Info {
            name: "Request span",
            kind: Kind::Request | Kind::Response,
        }
    }

    fn on_request(&self, request: &mut Request, _: &Data) {
        if let Some(RequestId(request_id)) = request.guard::<&RequestId>().succeeded() {
            let span = info_span!(
                "request",
                id = request_id.as_str(),
                method = request.method().as_str(),
                uri = request.uri().to_string().as_str(),
                status = Empty,
            );

            REQUEST_SPAN.with(|cell| cell.borrow_mut().replace(span.entered()));
        }
    }

    fn on_response(&self, _: &Request, response: &mut Response) {
        REQUEST_SPAN.with(|cell| {
            if let Some(span) = cell.borrow_mut().take() {
                let status = response.status();

                span.record("status", &status.code);
                if status.class().is_success() {
                    info!("request succeeded");
                } else {
                    warn!("request failed");
                }
            }
        });
    }
}
