use rocket::State;
use rocket_contrib::json::JsonValue;

use crate::application::Config;

#[get("/syntaxes")]
pub fn get_syntaxes(config: State<Config>) -> JsonValue {
    // This is a static route that simply returns a list of supported syntaxes.
    // Normally XSnippet API clients must inspect these values and use them with
    // submitted snippets.
    json!(config.syntaxes)
}
