use std::collections::BTreeSet;

use rocket::State;

use crate::application::Config;
use crate::errors::ApiError;
use crate::web::{NegotiatedContentType, Output};

#[get("/syntaxes")]
pub fn get_syntaxes(
    config: State<Config>,
    requested_content_type: Result<NegotiatedContentType, ApiError>,
) -> Result<Output<Option<BTreeSet<String>>>, ApiError> {
    let NegotiatedContentType(content_type) = requested_content_type?;

    // This is a static route that simply returns a list of supported syntaxes.
    // Normally XSnippet API clients must inspect these values and use them with
    // submitted snippets.
    Ok(Output(content_type, config.syntaxes.to_owned()))
}
