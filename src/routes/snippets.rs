use std::convert::TryFrom;

use percent_encoding::{utf8_percent_encode, AsciiSet, CONTROLS};
use rocket::http::uri::Origin;
use rocket::http::{HeaderMap, RawStr};
use rocket::response::status::Created;
use rocket::State;
use serde::Deserialize;

use crate::application::Config;
use crate::errors::ApiError;
use crate::storage::{Changeset, DateTime, Direction, ListSnippetsQuery, Snippet, Storage};
use crate::web::{
    BearerAuth, DoNotAcceptAny, Input, NegotiatedContentType, Output, PaginationLimit,
    WithHttpHeaders,
};

fn create_snippet_impl(
    storage: &dyn Storage,
    snippet: &Snippet,
    base_path: &str,
) -> Result<Created<Output<Snippet>>, ApiError> {
    let new_snippet = storage.create(snippet)?;

    let location = [base_path, new_snippet.id.as_str()].join("/");
    Ok(Created::new(location).body(Output(new_snippet)))
}

fn create_link_header(
    origin: &Origin,
    next_marker: Option<String>,
    prev_marker: Option<String>,
    prev_needed: bool,
) -> String {
    const QUERY_ENCODE_SET: &AsciiSet = &CONTROLS
        .add(b' ')
        .add(b'"')
        .add(b'#')
        .add(b'<')
        .add(b'>')
        .add(b'&');

    let query_wo_marker = origin.query().map(|q| {
        q.split('&')
            .filter_map(|v| {
                let v = RawStr::new(v).percent_decode_lossy();
                if !v.starts_with("marker=") {
                    Some(utf8_percent_encode(&v, QUERY_ENCODE_SET).to_string())
                } else {
                    None
                }
            })
            .collect::<Vec<_>>()
            .join("&")
    });
    let query_first = query_wo_marker.clone();
    let mut query_next = next_marker.map(|marker| format!("marker={}", marker));
    let mut query_prev = prev_marker.map(|marker| format!("marker={}", marker));

    // If a request URL does contain query parameters (other than marker), we
    // must reuse them together with next/prev markers.
    if let Some(query_wo_marker) = query_wo_marker {
        query_next = query_next.map(|query| format!("{}&{}", query_wo_marker, query));
        query_prev = query_prev.map(|query| format!("{}&{}", query_wo_marker, query));
    }

    // If a previous page is the first page, we don't have 'prev_marker' set
    // yet the link must be generated. If that's the case, reuse query
    // parameters we are using to generate a link to the first page.
    if query_prev.is_none() && prev_needed {
        query_prev = query_first.clone();
    }

    vec![
        // (query string, rel, is_required)
        (&query_first, "first", true),
        (&query_next, "next", query_next.is_some()),
        (&query_prev, "prev", prev_needed),
    ]
    .into_iter()
    .filter(|item| item.2)
    .map(|item| match item.0 {
        Some(query) => ([origin.path().as_str(), query.as_str()].join("?"), item.1),
        None => (origin.path().to_string(), item.1),
    })
    .map(|item| format!("<{}>; rel=\"{}\"", item.0, item.1))
    .collect::<Vec<_>>()
    .join(", ")
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
pub async fn create_snippet(
    config: &State<Config>,
    storage: &State<Box<dyn Storage>>,
    origin: &Origin<'_>,
    body: Result<Input<NewSnippet>, ApiError>,
    _content_type: &NegotiatedContentType,
    _user: BearerAuth,
) -> Result<Created<Output<Snippet>>, ApiError> {
    let snippet = Snippet::try_from((config.inner(), body?.0))?;
    create_snippet_impl(storage.as_ref(), &snippet, origin.path().as_str())
}

fn split_marker(mut snippets: Vec<Snippet>, limit: usize) -> (Option<String>, Vec<Snippet>) {
    if snippets.len() > limit {
        snippets.truncate(limit);
        (snippets.last().map(|m| m.id.to_owned()), snippets)
    } else {
        (None, snippets)
    }
}

#[allow(clippy::too_many_arguments)]
#[get("/snippets?<title>&<syntax>&<tag>&<marker>&<limit>")]
pub async fn list_snippets<'h>(
    storage: &State<Box<dyn Storage>>,
    origin: &Origin<'_>,
    title: Option<String>,
    syntax: Option<String>,
    tag: Option<String>,
    limit: Result<PaginationLimit, rocket::form::Errors<'_>>,
    marker: Option<String>,
    _content_type: &NegotiatedContentType,
    _user: BearerAuth,
) -> Result<WithHttpHeaders<'h, Output<Vec<Snippet>>>, ApiError> {
    let mut criteria = ListSnippetsQuery {
        title,
        syntax,
        tags: tag.map(|v| vec![v]),
        ..Default::default()
    };

    // Fetch one more record in order to detect if there's a next page, and
    // generate appropriate Link entry accordingly.
    let limit = limit
        .map_err(|e| ApiError::BadRequest(e.first().map(|e| e.to_string()).unwrap_or_default()))?
        .0;
    criteria.pagination.limit = limit + 1;
    criteria.pagination.marker = marker;

    let snippets = storage.list(criteria.clone())?;
    let mut prev_needed = false;
    let (next_marker, snippets) = split_marker(snippets, limit);
    let prev_marker = if criteria.pagination.marker.is_some() && !snippets.is_empty() {
        // In order to generate Link entry for previous page we have no choice
        // but to issue the query one more time into opposite direction.
        criteria.pagination.direction = Direction::Asc;
        criteria.pagination.marker = Some(snippets[0].id.to_owned());
        let prev_snippets = storage.list(criteria)?;
        prev_needed = !prev_snippets.is_empty();

        prev_snippets.get(limit).map(|m| m.id.to_owned())
    } else {
        None
    };

    let mut headers_map = HeaderMap::new();
    headers_map.add_raw(
        "Link",
        create_link_header(origin, next_marker, prev_marker, prev_needed),
    );

    Ok(WithHttpHeaders(headers_map, Some(Output(snippets))))
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
pub async fn import_snippet(
    config: &State<Config>,
    storage: &State<Box<dyn Storage>>,
    origin: &Origin<'_>,
    body: Result<Input<ImportSnippet>, ApiError>,
    user: BearerAuth,
    _content_type: &NegotiatedContentType,
) -> Result<Created<Output<Snippet>>, ApiError> {
    if !user.0.can_import_snippets() {
        return Err(ApiError::Forbidden(
            "User is not allowed to import snippets".to_string(),
        ));
    }

    let snippet = Snippet::try_from((config.inner(), body?.0))?;
    let path = origin.path();
    let base_path = path
        .strip_suffix("/import")
        .ok_or_else(|| ApiError::InternalError(format!("Invalid URI path: {}", path)))?;
    create_snippet_impl(storage.as_ref(), &snippet, base_path.as_str())
}

#[get("/snippets/<id>", format = "text/plain", rank = 1)]
pub async fn get_raw_snippet(
    storage: &State<Box<dyn Storage>>,
    id: String,
    _user: BearerAuth,
    // W/o this, a request specifying any media type (i.e. */*), would be matched by this route,
    // which is not what we want. We can't add the desired format to the route below, because it's
    // supposed to perform content negotiation and return an ApiError when a user requests an
    // unsupported format.
    _not_any: DoNotAcceptAny,
) -> Result<String, ApiError> {
    Ok(storage
        .get(&id)?
        .changesets
        .into_iter()
        .last()
        .map(|c| c.content)
        .unwrap_or_default())
}

#[get("/snippets/<id>", rank = 2)]
pub async fn get_snippet(
    storage: &State<Box<dyn Storage>>,
    id: String,
    _content_type: &NegotiatedContentType,
    _user: BearerAuth,
) -> Result<Output<Snippet>, ApiError> {
    Ok(Output(storage.get(&id)?))
}
