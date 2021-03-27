use std::convert::TryFrom;

use rocket::http::uri::Origin;
use rocket::response::status::Created;
use rocket::State;
use serde::Deserialize;

use crate::application::Config;
use crate::errors::ApiError;
use crate::storage::{Changeset, DateTime, Snippet, Storage};
use crate::web::{BearerAuth, Input, NegotiatedContentType, Output};

fn create_snippet_impl(
    storage: &dyn Storage,
    snippet: &Snippet,
    base_path: &str,
) -> Result<Created<Output<Snippet>>, ApiError> {
    let new_snippet = storage.create(snippet)?;

    let location = vec![base_path.to_string(), new_snippet.id.to_string()].join("/");
    Ok(Created(location, Some(Output(new_snippet))))
}

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

impl TryFrom<(&Config, NewSnippet)> for Snippet {
    type Error = ApiError;

    fn try_from((config, value): (&Config, NewSnippet)) -> Result<Self, Self::Error> {
        if value.content.is_empty() {
            return Err(ApiError::BadRequest(String::from(
                "`content` - empty values not allowed.",
            )));
        }
        if let Some(syntax) = &value.syntax {
            if let Some(allowed_syntaxes) = &config.syntaxes {
                if !allowed_syntaxes.contains(syntax) {
                    return Err(ApiError::BadRequest(format!(
                        "`syntax` - unallowed value {}.",
                        syntax
                    )));
                }
            }
        }

        Ok(Snippet::new(
            value.title,
            value.syntax,
            vec![Changeset::new(0, value.content)],
            value.tags.unwrap_or_default(),
        ))
    }
}

#[post("/snippets", data = "<body>")]
pub fn create_snippet(
    config: State<Config>,
    storage: State<Box<dyn Storage>>,
    origin: &Origin,
    body: Result<Input<NewSnippet>, ApiError>,
    _content_type: NegotiatedContentType,
    _user: BearerAuth,
) -> Result<Created<Output<Snippet>>, ApiError> {
    let snippet = Snippet::try_from((&*config, body?.0))?;
    create_snippet_impl(&**storage, &snippet, origin.path())
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ImportSnippet {
    #[serde(flatten)]
    pub new_snippet: NewSnippet,
    /// Snippet identifier.
    pub id: Option<String>,
    /// Snippet creation date. May be omitted in the user request.
    pub created_at: Option<DateTime>,
    /// Snippet modification date. May be omitted in the user request.
    pub updated_at: Option<DateTime>,
}

impl TryFrom<(&Config, ImportSnippet)> for Snippet {
    type Error = ApiError;

    fn try_from((config, value): (&Config, ImportSnippet)) -> Result<Self, Self::Error> {
        let mut snippet = Snippet::try_from((config, value.new_snippet))?;
        if let Some(id) = value.id {
            snippet.id = id;
        }
        if value.created_at.is_some() {
            snippet.created_at = value.created_at;
        }
        if value.updated_at.is_some() {
            snippet.updated_at = value.updated_at;
        }

        Ok(snippet)
    }
}

#[post("/snippets/import", data = "<body>")]
pub fn import_snippet(
    config: State<Config>,
    storage: State<Box<dyn Storage>>,
    origin: &Origin,
    body: Result<Input<ImportSnippet>, ApiError>,
    user: BearerAuth,
    _content_type: NegotiatedContentType,
) -> Result<Created<Output<Snippet>>, ApiError> {
    if !user.0.can_import_snippets() {
        return Err(ApiError::Forbidden(
            "User is not allowed to import snippets".to_string(),
        ));
    }

    let snippet = Snippet::try_from((&*config, body?.0))?;
    let base_path = origin
        .path()
        .strip_suffix("/import")
        .ok_or_else(|| ApiError::InternalError(format!("Invalid URI path: {}", origin.path())))?;
    create_snippet_impl(&**storage, &snippet, base_path)
}

#[get("/snippets/<id>")]
pub fn get_snippet(
    storage: State<Box<dyn Storage>>,
    id: String,
    _user: BearerAuth,
) -> Result<Output<Snippet>, ApiError> {
    Ok(Output(storage.get(&id)?))
}
