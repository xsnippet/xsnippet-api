use std::cell::RefCell;

use rocket::fairing::{Fairing, Info, Kind};
use rocket::outcome::Outcome;
use rocket::request::{self, FromRequest, Request};
use rocket::{Data, Response};
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

#[rocket::async_trait]
impl<'r> FromRequest<'r> for &'r RequestId {
    type Error = ();

    async fn from_request(request: &'r Request<'_>) -> request::Outcome<Self, Self::Error> {
        // on first access, generate a new value and store it in the request cache
        Outcome::Success(request.local_cache(RequestId::default))
    }
}

/// Rocket fairing that returns the identifier of the API request in the
/// X-Request-Id response header.
pub struct RequestIdHeader;

#[rocket::async_trait]
impl Fairing for RequestIdHeader {
    fn info(&self) -> Info {
        Info {
            name: "X-Request-Id response header",
            kind: Kind::Response,
        }
    }

    async fn on_response<'r>(&self, request: &'r Request<'_>, response: &mut Response<'r>) {
        if let Some(request_id) = request.guard::<&RequestId>().await.succeeded() {
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

// TODO: Now that Rocket is using async internally, this is not guaranteed to
// work correctly anymore, as tokio might execute the fairing and the request
// handler on different OS threads. I haven't found a way to fix this. We will
// need to wait for https://github.com/SergioBenitez/Rocket/pull/1579 that
// creates a tracing span in Rocket itself and attaches it to the top-level
// request future.
//
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
thread_local!(static REQUEST_SPAN: RefCell<Option<EnteredSpan>> = const { RefCell::new(None) });

#[rocket::async_trait]
impl Fairing for RequestSpan {
    fn info(&self) -> Info {
        Info {
            name: "Request span",
            kind: Kind::Request | Kind::Response,
        }
    }

    async fn on_request(&self, request: &mut Request<'_>, _: &mut Data<'_>) {
        if let Some(RequestId(request_id)) = request.guard::<&RequestId>().await.succeeded() {
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

    async fn on_response<'r>(&self, _: &'r Request<'_>, response: &mut Response<'r>) {
        REQUEST_SPAN.with(|cell| {
            if let Some(span) = cell.borrow_mut().take() {
                let status = response.status();

                span.record("status", status.code);
                if status.class().is_success() {
                    info!("request succeeded");
                } else {
                    warn!("request failed");
                }
            }
        });
    }
}
