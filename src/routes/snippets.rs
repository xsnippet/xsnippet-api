use std::collections::BTreeSet;
use std::path::PathBuf;

use rocket::http::uri::Origin;
use rocket::response::status::Created;
use rocket::State;
use serde::Deserialize;

use crate::application::Config;
use crate::errors::ApiError;
use crate::storage::{Changeset, Snippet, Storage};
use crate::web::{Input, NegotiatedContentType, Output};

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

fn build_location(origin: &Origin, relative_path: &str) -> Result<String, ApiError> {
    // TODO(malor): verify that this works correctly on other systems
    let new_path = PathBuf::from(origin.path()).join(relative_path);
    Ok(new_path
        .to_str()
        .ok_or_else(|| {
            ApiError::InternalError(format!("Could not construct Location from: {:?}", new_path))
        })?
        .to_owned())
}

#[post("/snippets", data = "<body>")]
pub fn create_snippet(
    config: State<Config>,
    storage: State<Box<dyn Storage>>,
    origin: &Origin,
    requested_content_type: Result<NegotiatedContentType, ApiError>,
    body: Result<Input<NewSnippet>, ApiError>,
) -> Result<Created<Output<Snippet>>, ApiError> {
    let NegotiatedContentType(content_type) = requested_content_type?;

    let new_snippet = storage.create(&body?.0.validate(config.syntaxes.as_ref())?)?;

    let location = build_location(origin, &new_snippet.id)?;
    Ok(Created(location, Some(Output(content_type, new_snippet))))
}
