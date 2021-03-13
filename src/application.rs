use std::collections::BTreeSet;
use std::error::Error;

use super::routes;
use super::storage::{SqlStorage, Storage};
use super::web::RequestIdHeader;

#[derive(Debug)]
pub struct Config {
    /// Keeps a set of supported syntaxes. When set, RESTful API rejects
    /// snippets with *unsupported* syntaxes. Normally this set must be
    /// kept in sync with a set of supported syntaxes in XSnippet Web in
    /// order to ensure that the web part can properly syntax-highlight
    /// snippets.
    pub syntaxes: Option<BTreeSet<String>>,
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
    let storage: Box<dyn Storage> = Box::new(SqlStorage::new(&database_url)?);

    let routes = routes![
        routes::snippets::create_snippet,
        routes::snippets::get_snippet,
        routes::syntaxes::get_syntaxes,
    ];
    Ok(app
        .manage(Config { syntaxes })
        .manage(storage)
        .attach(RequestIdHeader)
        .mount("/v1", routes))
}
