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
extern crate rocket_contrib;

mod application;
mod errors;
mod routes;
mod storage;
mod util;

fn main() {
    let app = match application::create_app() {
        Ok(app) => app,
        Err(err) => {
            eprintln!("error: {}", err);
            std::process::exit(1);
        }
    };
    app.launch();
}
