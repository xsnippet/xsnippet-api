use std::collections::BTreeSet;
use std::error::Error;

use super::routes;
use super::storage::{SqlStorage, Storage};
use super::web::{AuthValidator, JwtValidator, RequestIdHeader, RequestSpan};

#[derive(Debug)]
pub struct Config {
    /// Keeps a set of supported syntaxes. When set, RESTful API rejects
    /// snippets with *unsupported* syntaxes. Normally this set must be
    /// kept in sync with a set of supported syntaxes in XSnippet Web in
    /// order to ensure that the web part can properly syntax-highlight
    /// snippets.
    pub syntaxes: Option<BTreeSet<String>>,

    /// The intended recipient of the tokens (e.g. "https://api.xsnippet.org")
    pub jwt_audience: String,
    /// The principal that issues the tokens (e.g. "https://xsnippet.eu.auth0.com/")
    pub jwt_issuer: String,
    /// The location of JWT Key Set with keys used to validate the tokens (e.g. "https://xsnippet.eu.auth0.com/.well-known/jwks.json")
    pub jwt_jwks_uri: String,
}

/// Create and return a Rocket application instance.
///
/// # Errors
///
/// Returns `Err(rocket::config::ConfigError)` if configuration supplied
/// cannot be parsed or invalid.
pub fn create_app() -> Result<rocket::Rocket, Box<dyn Error>> {
    let app = rocket::ignite();

    let syntaxes = app.config().get_slice("syntaxes");
    let syntaxes = match syntaxes {
        Ok(syntaxes) => Some(
            syntaxes
                .iter()
                .map(|v| v.clone().try_into::<String>())
                .collect::<Result<BTreeSet<_>, _>>()?,
        ),
        Err(rocket::config::ConfigError::Missing(_)) => None,
        Err(err) => return Err(Box::new(err)),
    };

    let database_url = match app.config().get_string("database_url") {
        Ok(database_url) => database_url,
        Err(err) => return Err(Box::new(err)),
    };

    let config = Config {
        syntaxes,
        jwt_audience: app
            .config()
            .get_string("jwt_audience")
            .unwrap_or_else(|_| String::from("https://api.xsnippet.org")),
        jwt_issuer: app
            .config()
            .get_string("jwt_issuer")
            .unwrap_or_else(|_| String::from("https://xsnippet.eu.auth0.com/")),
        jwt_jwks_uri: app.config().get_string("jwt_jwks_uri").unwrap_or_else(|_| {
            String::from("https://xsnippet.eu.auth0.com/.well-known/jwks.json")
        }),
    };

    let storage: Box<dyn Storage> = Box::new(SqlStorage::new(&database_url)?);
    let token_validator: Box<dyn AuthValidator> = Box::new(JwtValidator::from_config(&config)?);

    let routes = routes![
        routes::snippets::create_snippet,
        routes::snippets::get_snippet,
        routes::syntaxes::get_syntaxes,
        routes::snippets::import_snippet,
    ];
    Ok(app
        .manage(config)
        .manage(storage)
        .manage(token_validator)
        .attach(RequestIdHeader)
        .attach(RequestSpan)
        .mount("/v1", routes))
}
