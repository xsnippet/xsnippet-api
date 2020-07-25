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
mod routes;
mod storage;

fn main() {
    let app = application::create_app();
    app.launch();
}
