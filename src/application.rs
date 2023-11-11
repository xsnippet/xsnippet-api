use std::collections::BTreeSet;

use rocket::fairing::AdHoc;
use serde::Deserialize;

use super::routes;
use super::storage::{SqlStorage, Storage};
use super::web::{AuthValidator, JwtValidator, RequestIdHeader};

#[derive(Debug, Deserialize)]
pub struct Config {
    /// Database connection string
    pub database_url: String,

    /// Keeps a set of supported syntaxes. When set, RESTful API rejects
    /// snippets with *unsupported* syntaxes. Normally this set must be
    /// kept in sync with a set of supported syntaxes in XSnippet Web in
    /// order to ensure that the web part can properly syntax-highlight
    /// snippets.
    #[serde(default)]
    pub syntaxes: Option<BTreeSet<String>>,

    /// The intended recipient of the tokens (e.g. "https://api.xsnippet.org")
    #[serde(default = "default_jwt_audience")]
    pub jwt_audience: String,
    /// The principal that issues the tokens (e.g. "https://xsnippet.eu.auth0.com/")
    #[serde(default = "default_jwt_issuer")]
    pub jwt_issuer: String,
    /// The location of JWT Key Set with keys used to validate the tokens (e.g. "https://xsnippet.eu.auth0.com/.well-known/jwks.json")
    #[serde(default = "default_jwks_uri")]
    pub jwt_jwks_uri: String,
}

fn default_jwt_audience() -> String {
    "https://api.xsnippet.org".to_string()
}
fn default_jwt_issuer() -> String {
    "https://xsnippet.eu.auth0.com/".to_string()
}
fn default_jwks_uri() -> String {
    "https://xsnippet.eu.auth0.com/.well-known/jwks.json".to_string()
}

/// Create and return a Rocket application instance.
pub fn create_app() -> rocket::Rocket<rocket::Build> {
    let app = rocket::build().attach(AdHoc::try_on_ignite("Config", |app| async {
        let config = match app.figment().extract::<Config>() {
            Ok(config) => config,
            Err(e) => {
                error!("Failed to read config: {}", e);
                return Err(app);
            }
        };
        let storage: Box<dyn Storage> = match SqlStorage::new(&config.database_url) {
            Ok(storage) => Box::new(storage),
            Err(e) => {
                error!("Failed to create a storage connection: {}", e);
                return Err(app);
            }
        };
        let auth: Box<dyn AuthValidator> = match JwtValidator::from_config(&config).await {
            Ok(auth) => Box::new(auth),
            Err(e) => {
                error!("Failed to create an auth validator: {}", e);
                return Err(app);
            }
        };

        Ok(app
            .manage(config)
            .manage(storage)
            .manage(auth)
            .attach(RequestIdHeader))
    }));

    let routes = routes![
        routes::snippets::create_snippet,
        routes::snippets::list_snippets,
        routes::snippets::get_snippet,
        routes::snippets::get_raw_snippet,
        routes::syntaxes::get_syntaxes,
        routes::snippets::import_snippet,
    ];
    app.mount("/v1", routes)
}
