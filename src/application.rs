use super::routes;

pub fn create_app() -> rocket::Rocket {
    rocket::ignite().mount("/v1", routes![routes::syntaxes::get_syntaxes])
}
