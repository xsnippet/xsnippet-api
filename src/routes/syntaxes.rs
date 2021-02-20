use std::collections::BTreeSet;

use rocket::State;

use crate::application::Config;
use crate::errors::ApiError;
use crate::web::Output;

#[get("/syntaxes")]
pub fn get_syntaxes(config: State<Config>) -> Result<Output<Option<BTreeSet<String>>>, ApiError> {
    // This is a static route that simply returns a list of supported syntaxes.
    // Normally XSnippet API clients must inspect these values and use them with
    // submitted snippets.
    Ok(Output(config.syntaxes.to_owned()))
}
