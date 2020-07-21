use rocket_contrib::json::JsonValue;

#[get("/syntaxes")]
pub fn get_syntaxes() -> JsonValue {
    json!(["rust"])
}
