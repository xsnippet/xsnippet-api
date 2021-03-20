//! # XSnippet API
//!
//! XSnippet API is a RESTful API for a simple web-service for sharing code
//! snippets on the Internet.

#![feature(proc_macro_hygiene, decl_macro)]

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

fn main() {
    // set up logging of application events to stderr
    let tracing_config = rocket::config::RocketConfig::active_default()
        .expect("failed to read Rocket config")
        .active()
        .get_string("tracing")
        .unwrap_or_else(|_| String::from("info"));
    let subscriber = fmt()
        .with_env_filter(EnvFilter::new(tracing_config))
        .with_writer(std::io::stderr)
        .finish();
    tracing::subscriber::set_global_default(subscriber).expect("setting default subscriber failed");

    let app = match application::create_app() {
        Ok(app) => app,
        Err(err) => {
            error!("error: {}", err);
            std::process::exit(1);
        }
    };
    app.launch();
}
