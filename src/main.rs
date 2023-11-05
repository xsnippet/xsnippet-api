//! # XSnippet API
//!
//! XSnippet API is a RESTful API for a simple web-service for sharing code
//! snippets on the Internet.

// Clippy bug: https://github.com/rust-lang/rust-clippy/issues/7422
#![allow(clippy::nonstandard_macro_braces)]

#[macro_use]
extern crate diesel;
#[macro_use]
extern crate rocket;
#[macro_use]
extern crate tracing;

mod application;
mod errors;
mod routes;
mod storage;
mod web;

use tracing_subscriber::{fmt, EnvFilter};

#[rocket::launch]
async fn rocket() -> _ {
    // set up logging of application events to stderr
    let tracing_config = rocket::config::Config::figment()
        .extract_inner::<String>("tracing")
        .unwrap_or_else(|_| String::from("info"));
    let subscriber = fmt()
        .with_env_filter(EnvFilter::new(tracing_config))
        .with_writer(std::io::stderr)
        .finish();
    tracing::subscriber::set_global_default(subscriber).expect("setting default subscriber failed");

    application::create_app()
}
