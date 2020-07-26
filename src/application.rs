use std::collections::HashSet;
use std::error::Error;

use super::routes;

#[derive(Debug)]
pub struct Config {
    /// Keeps a set of supported syntaxes. When set, RESTful API rejects
    /// snippets with *unsupported* syntaxes. Normally this set must be
    /// kept in sync with a set of supported syntaxes in XSnippet Web in
    /// order to ensure that the web part can properly syntax-highlight
    /// snippets.
    pub syntaxes: Option<HashSet<String>>,
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
                .collect::<Result<HashSet<_>, _>>()?,
        ),
        Err(rocket::config::ConfigError::Missing(_)) => None,
        Err(err) => return Err(Box::new(err)),
    };

    Ok(app
        .manage(Config { syntaxes: syntaxes })
        .mount("/v1", routes![routes::syntaxes::get_syntaxes]))
}
