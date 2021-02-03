use std::collections::BTreeSet;

use rocket::http::uri::Origin;
use rocket::response::status::Created;
use rocket::State;
use rocket_contrib::json::JsonValue;
use serde::Deserialize;

use crate::application::Config;
use crate::errors::ApiError;
use crate::storage::{Changeset, Snippet, Storage};
use crate::util::Input;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewSnippet {
    /// Snippet title. May be omitted in the user request.
    pub title: Option<String>,
    /// Snippet syntax. May be omitted in the user request.
    pub syntax: Option<String>,
    /// Snippet content. Must be specified in the user request. Can't be empty.
    pub content: String,
    /// List of tags attached to the snippet. May be omitted in the user
    /// request.
    pub tags: Option<Vec<String>>,
}

impl NewSnippet {
    pub fn validate(
        self,
        allowed_syntaxes: Option<&BTreeSet<String>>,
    ) -> Result<Snippet, ApiError> {
        if self.content.is_empty() {
            return Err(ApiError::BadRequest(String::from(
                "`content` - empty values not allowed.",
            )));
        }
        if let Some(syntax) = &self.syntax {
            if let Some(allowed_syntaxes) = &allowed_syntaxes {
                if !allowed_syntaxes.contains(syntax) {
                    return Err(ApiError::BadRequest(format!(
                        "`syntax` - unallowed value {}.",
                        syntax
                    )));
                }
            }
        }

        Ok(Snippet::new(
            self.title,
            self.syntax,
            vec![Changeset::new(0, self.content)],
            self.tags.unwrap_or_default(),
        ))
    }
}

#[post("/snippets", data = "<body>")]
pub fn create_snippet(
    origin: &Origin,
    config: State<Config>,
    storage: State<Box<dyn Storage>>,
    body: Result<Input<NewSnippet>, ApiError>,
) -> Result<Created<JsonValue>, ApiError> {
    let new_snippet = storage.create(&body?.0.validate(config.syntaxes.as_ref())?)?;

    let location = vec![origin.path().to_string(), new_snippet.id.to_string()].join("/");
    let response = json!(new_snippet);

    Ok(Created(location, Some(response)))
}

#[get("/snippets/<id>")]
pub fn get_snippet(storage: State<Box<dyn Storage>>, id: String) -> Result<JsonValue, ApiError> {
    Ok(json!(storage.get(&id)?))
}
