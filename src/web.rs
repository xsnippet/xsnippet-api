mod content;
mod tracing;

pub use crate::web::content::{Input, NegotiatedContentType, Output};
pub use crate::web::tracing::{RequestId, RequestIdHeader, RequestSpan};
