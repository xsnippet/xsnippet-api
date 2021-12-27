use std::collections::BTreeSet;
use std::fmt;

use rocket::State;
use serde::Serialize;

use crate::application::Config;
use crate::errors::ApiError;
use crate::web::Output;

#[derive(Serialize)]
pub struct Syntaxes(pub Option<BTreeSet<String>>);

impl fmt::Display for Syntaxes {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if let Some(value) = &self.0 {
            for s in value.iter() {
                writeln!(f, "{}", s)?
            }
        }

        Ok(())
    }
}

#[get("/syntaxes")]
pub fn get_syntaxes(config: State<Config>) -> Result<Output<Syntaxes>, ApiError> {
    // This is a static route that simply returns a list of supported syntaxes.
    // Normally XSnippet API clients must inspect these values and use them with
    // submitted snippets.
    Ok(Output(Syntaxes(config.syntaxes.to_owned())))
}
