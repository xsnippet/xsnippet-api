use jsonwebtoken::{Algorithm, Validation};
use serde::{Deserialize, Serialize};

use super::{AuthValidator, Error, Permission, Result, User};
use crate::application::Config;

const SUPPORTED_ALGORITHMS: [Algorithm; 3] = [Algorithm::RS256, Algorithm::RS384, Algorithm::RS512];

/// JSON Web Key. A cryptographic key used to validate JSON Web Tokens.
#[derive(Debug, PartialEq, Deserialize, Serialize)]
struct Key {
    alg: Algorithm,
    kty: String,
    r#use: String,
    n: String,
    e: String,
    kid: String,
    x5t: String,
    x5c: Vec<String>,
}

/// JSON Web Key Set. A collection of JSON Web Keys used by a given service.
#[derive(Debug, PartialEq, Deserialize, Serialize)]
struct Jwks {
    keys: Vec<Key>,
}

impl Jwks {
    /// Looks up the key by id, or returns None if it's not present in the key
    /// set.
    pub fn find(&self, key_id: &str) -> Option<&Key> {
        self.keys.iter().find(|key| key.kid == key_id)
    }
}

/// A set of values encoded in a JWT that the issuer claims to be true.
#[derive(Debug, Deserialize)]
struct Claims {
    /// Audience (who or that the token is intended for). E.g. "https://api.xsnippet.org".
    aud: String,
    /// Issuer (who created and signed this token). E.g. "https://xsnippet.eu.auth0.com/".
    iss: String,
    /// Subject (whom the token refers to). E.g. "spam@eggs.foo".
    sub: String,
    /// Expiration time (seconds since Unix epoch).
    exp: usize,
    /// Subject permissions (e.g. vec!["import"])
    permissions: Vec<Permission>,
}

impl Jwks {
    /// Returns a Jwks retrieved from the location identified by the given URI.
    pub fn from_uri(uri: &str) -> Result<Self> {
        let load_err = Error::Configuration(format!("Can't load Jwks state from {}", uri));
        let json = match uri.split_once("://") {
            Some(("https", _)) => reqwest::blocking::get(uri)
                .and_then(|response| response.text())
                .map_err(|_| load_err)?,
            Some(("file", path)) => std::fs::read_to_string(path).map_err(|_| load_err)?,
            _ => {
                return Err(Error::Configuration(
                    "URI scheme is not supported or URI is invalid".to_string(),
                ))
            }
        };

        let jwks = serde_json::from_slice::<Jwks>(json.as_bytes())
            .map_err(|_| Error::Configuration("Can't parse Jwks state as JSON".to_string()))?;

        if !jwks.keys.is_empty() {
            Ok(jwks)
        } else {
            Err(Error::Configuration("Jwks is empty".to_string()))
        }
    }
}

/// A facade for validation of JWT values.
pub struct JwtValidator {
    jwks: Jwks,
    validation: Validation,
}

impl JwtValidator {
    /// Returns a new JwtValidator constructed from the given parameters.
    ///
    /// # Arguments
    ///
    /// * `audience` - The intended recipient of the tokens (e.g. "https://api.xsnippet.org")
    /// * `issuer`   - The principal that issues the tokens (e.g. "https://xsnippet.eu.auth0.com/")
    /// * `jwks_uri` - The location of JWT Key Set with keys used to validate the tokens (e.g. "https://xsnippet.eu.auth0.com/.well-known/jwks.json")
    pub fn new(audience: String, issuer: String, jwks_uri: &str) -> Result<Self> {
        let jwks = Jwks::from_uri(jwks_uri)?;

        //  The following token properties are going to be verified:
        //  * the expiration time
        //  * the issuer
        //  * the intended audience
        let validation = Validation {
            algorithms: SUPPORTED_ALGORITHMS.to_vec(),
            aud: Some(std::iter::once(audience).collect()),
            iss: Some(issuer),
            ..Validation::default()
        };

        Ok(JwtValidator { jwks, validation })
    }

    /// Returns a new JwtValidator constructed from the application config.
    pub fn from_config(config: &Config) -> Result<Self> {
        JwtValidator::new(
            config.jwt_audience.to_owned(),
            config.jwt_issuer.to_owned(),
            &config.jwt_jwks_uri,
        )
    }
}

impl AuthValidator for JwtValidator {
    fn validate(&self, token: &str) -> Result<User> {
        let header =
            jsonwebtoken::decode_header(token).map_err(|err| Error::Input(err.to_string()))?;

        let key = match header.alg {
            Algorithm::RS256 | Algorithm::RS384 | Algorithm::RS512 => {
                let key_id = header
                    .kid
                    .as_ref()
                    .ok_or_else(|| Error::Input("Token does not specify the key id".to_string()))?;

                let key = self
                    .jwks
                    .find(&key_id)
                    .filter(|key| key.alg == header.alg && key.r#use == "sig")
                    .ok_or_else(|| {
                        Error::Configuration(format!("Signing key {:?} can't be found", key_id))
                    })?;

                jsonwebtoken::DecodingKey::from_rsa_components(&key.n, &key.e)
            }
            alg => return Err(Error::Input(format!("Unsupported algorithm: {:?}", alg))),
        };

        match jsonwebtoken::decode::<Claims>(&token, &key, &self.validation) {
            Ok(data) => Ok(User::Authenticated {
                name: data.claims.sub,
                permissions: data.claims.permissions,
            }),
            Err(err) => Err(Error::Validation(err.to_string())),
        }
    }
}

#[cfg(test)]
mod tests {
    use std::io::BufWriter;
    use std::{io::Write, path::Path};

    use super::*;

    const KID: &str = "test-key";
    const AUDIENCE: &str = "xsnippet-api-tests-aud";
    const ISSUER: &str = "xsnippet-api-tests-iss";
    const N: &str = "qN5dCh1M2RA3aF6ZH4IRXIQYKvaWRG59F7lpQIUyUtkDiURmVem7x86EuGmmTmQPSRhx6fL4jF0GBkduAhYnFn_A8T6WfQXzXyI2cyqXsKaTkDMKvl7nHnGttQIuG8W2m7H74pklsPKxp0rPJ0zjV1N_lr_nZG_dayJhtEnChHpScaoTwqMitcOJfVacNxcRbTSDy1IZY5AW0TLdATUmc-ddJLQXxSV7bMur_4S1MP45tHrttChgtnmPpL3q4MHZjHR8aNRYPurkJkPwY0t6nrERTPk9DE4Mk5NtNzqZRBY7eT94pmodVUBGTVYhh7bFDGB26oyTk8_5aedO6syB6w==";
    const E: &str = "AQAB";

    const USER_TOKEN: &str = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6InRlc3Qta2V5In0.eyJzdWIiOiJ1c2VyIiwiYXVkIjoieHNuaXBwZXQtYXBpLXRlc3RzLWF1ZCIsImlzcyI6InhzbmlwcGV0LWFwaS10ZXN0cy1pc3MiLCJleHAiOjQ3NzAzNzU1NDQsInBlcm1pc3Npb25zIjpbXX0.doA6EeVLnp-MLNRTRUzg03rw9oUn5vDGv59zNysrcFfvkEiiYAtZMu-YW_N3YtE0qv2FTaGAXHryMqsEk8rsFv4uepDuOpzutnRoB4JDFTpvJkKYE4HZjsd8eHSAjFEuCvDjm7wnxoW0zDXH_zj1FITht-c3ua6KbgeevvDjpUgaR52Zou9HRyNa6ns5OKO7yJofA32IZaO7QH69iQiZ4o9WA8PfFNyuVqyQVkvZwpr68JLgl4qTTX4NIWV4wU4OWbIGN6-p4QSkS_Ljkau9sRKjnx4NYPbICMGWVThn_MKOfg26DjGZlI_0HFYDBLogJkTmmyT-5IIIWUqBgUKWYA";
    const EXPIRED_TOKEN: &str = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6InRlc3Qta2V5In0.eyJzdWIiOiJ1c2VyIiwiYXVkIjoieHNuaXBwZXQtYXBpLXRlc3RzLWF1ZCIsImlzcyI6InhzbmlwcGV0LWFwaS10ZXN0cy1pc3MiLCJleHAiOjE2MTY3NzIwMDYsInBlcm1pc3Npb25zIjpbXX0.AkC-xzeJ7OXi5fN-DXs43vKAjgsep5Cwx2e1c3hbv1jPpJVnwTD2M_A8Bphd8-mzMsuO017a_rZQIj30dzt3I5Z730Z4zHA_xPV4nl_6zsGzCYTwecT1qmOhTuiyP1PhdgveVQz-ImNDbAzD80PTUwW8Bv-r4R1wyrc5lRtj2ofF1h2_rqxWtRbQwvqmm_J4K8oklYWOrBPNFXJVOGVcji97LelBY6llWbfVUO2unNZBA7MbJLDMtuQHMIRSHn1PXSLA4MJbxOzT-kZC01OlpQWtGstxnITHc34ZDVe5M0v092PSe5J0o3_OBVCR405-rPK_EjLD8saPE3SK7X0Cfw";
    const INVALID_TOKEN: &str = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6InRlc3Qta2V5In0.eyJzdWIiOiJ1c2VyIiwiYXVkIjoieHNuaXBwZXQtYXBpLXRlc3RzLWF1ZCIsImlzcyI6InhzbmlwcGV0LWFwaS10ZXN0cy1pc3MiLCJleHAiOjQ3NzAzNzU1NDQsInBlcm1pc3Npb25zIjpbXX0.doA6EeVLnp-MLNRTRUzg03rw9oUn5vDGv59zNysrcFfvkEiiYAtZMu-YW_N3YtE0qv2FTaGAXHryMqsEk8rsFv4uepDuOpzutnRoB4JDFTpvJkKYE4HZjsd8eHSAjFEuCvDjm7wnxoW0zDXH_zj1FITht-c3ua6KbgeevvDjpUgaR52Zou9HRyNa6ns5OKO7yJofA32IZaO7QH69iQiZ4o9WA8PfFNyuVqyQVkvZwpr68JLgl4qTTX4NIWV4wU4OWbIGN6-p3QSkS_Ljkau9sRKjnx4NYPbICMGWVThn_MKOfg26DjGZlI_0HFYDBLogJkTmmyT-5IIIWUqBgUKWYA";
    const INVALID_HEADER_TOKEN: &str = "eyJ0eXAiOiJKV1QiLCJraWQiOiJ0ZXN0LWtleSJ9.eyJzdWIiOiJ1c2VyIiwiYXVkIjoieHNuaXBwZXQtYXBpLXRlc3RzLWF1ZCIsImlzcyI6InhzbmlwcGV0LWFwaS10ZXN0cy1pc3MiLCJleHAiOjQ3NzAzNzU1NDQsInBlcm1pc3Npb25zIjpbXX0.doA6EeVLnp-MLNRTRUzg03rw9oUn5vDGv59zNysrcFfvkEiiYAtZMu-YW_N3YtE0qv2FTaGAXHryMqsEk8rsFv4uepDuOpzutnRoB4JDFTpvJkKYE4HZjsd8eHSAjFEuCvDjm7wnxoW0zDXH_zj1FITht-c3ua6KbgeevvDjpUgaR52Zou9HRyNa6ns5OKO7yJofA32IZaO7QH69iQiZ4o9WA8PfFNyuVqyQVkvZwpr68JLgl4qTTX4NIWV4wU4OWbIGN6-p4QSkS_Ljkau9sRKjnx4NYPbICMGWVThn_MKOfg26DjGZlI_0HFYDBLogJkTmmyT-5IIIWUqBgUKWYA";
    const NO_KID_TOKEN: &str = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyIiwiYXVkIjoieHNuaXBwZXQtYXBpLXRlc3RzLWF1ZCIsImlzcyI6InhzbmlwcGV0LWFwaS10ZXN0cy1pc3MiLCJleHAiOjQ3NzAzNzU1NDQsInBlcm1pc3Npb25zIjpbXX0.doA6EeVLnp-MLNRTRUzg03rw9oUn5vDGv59zNysrcFfvkEiiYAtZMu-YW_N3YtE0qv2FTaGAXHryMqsEk8rsFv4uepDuOpzutnRoB4JDFTpvJkKYE4HZjsd8eHSAjFEuCvDjm7wnxoW0zDXH_zj1FITht-c3ua6KbgeevvDjpUgaR52Zou9HRyNa6ns5OKO7yJofA32IZaO7QH69iQiZ4o9WA8PfFNyuVqyQVkvZwpr68JLgl4qTTX4NIWV4wU4OWbIGN6-p4QSkS_Ljkau9sRKjnx4NYPbICMGWVThn_MKOfg26DjGZlI_0HFYDBLogJkTmmyT-5IIIWUqBgUKWYA";
    const UNKNOWN_KID_TOKEN: &str = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImVnZ3MifQ.eyJzdWIiOiJ1c2VyIiwiYXVkIjoieHNuaXBwZXQtYXBpLXRlc3RzLWF1ZCIsImlzcyI6InhzbmlwcGV0LWFwaS10ZXN0cy1pc3MiLCJleHAiOjQ3NzAzNzU1NDQsInBlcm1pc3Npb25zIjpbXX0.doA6EeVLnp-MLNRTRUzg03rw9oUn5vDGv59zNysrcFfvkEiiYAtZMu-YW_N3YtE0qv2FTaGAXHryMqsEk8rsFv4uepDuOpzutnRoB4JDFTpvJkKYE4HZjsd8eHSAjFEuCvDjm7wnxoW0zDXH_zj1FITht-c3ua6KbgeevvDjpUgaR52Zou9HRyNa6ns5OKO7yJofA32IZaO7QH69iQiZ4o9WA8PfFNyuVqyQVkvZwpr68JLgl4qTTX4NIWV4wU4OWbIGN6-p4QSkS_Ljkau9sRKjnx4NYPbICMGWVThn_MKOfg26DjGZlI_0HFYDBLogJkTmmyT-5IIIWUqBgUKWYA";
    const UNSUPPORTED_ALG_TOKEN: &str = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiIsImtpZCI6InRlc3Qta2V5In0.eyJzdWIiOiJ1c2VyIiwiYXVkIjoieHNuaXBwZXQtYXBpLXRlc3RzLWF1ZCIsImlzcyI6InhzbmlwcGV0LWFwaS10ZXN0cy1pc3MiLCJleHAiOjQ3NzAzNzU1NDQsInBlcm1pc3Npb25zIjpbXX0.doA6EeVLnp-MLNRTRUzg03rw9oUn5vDGv59zNysrcFfvkEiiYAtZMu-YW_N3YtE0qv2FTaGAXHryMqsEk8rsFv4uepDuOpzutnRoB4JDFTpvJkKYE4HZjsd8eHSAjFEuCvDjm7wnxoW0zDXH_zj1FITht-c3ua6KbgeevvDjpUgaR52Zou9HRyNa6ns5OKO7yJofA32IZaO7QH69iQiZ4o9WA8PfFNyuVqyQVkvZwpr68JLgl4qTTX4NIWV4wU4OWbIGN6-p4QSkS_Ljkau9sRKjnx4NYPbICMGWVThn_MKOfg26DjGZlI_0HFYDBLogJkTmmyT-5IIIWUqBgUKWYA";

    fn with_jwks<F>(test: F)
    where
        F: FnOnce(&Path),
    {
        let jwks = Jwks {
            keys: vec![Key {
                alg: Algorithm::RS256,
                kty: String::from("RSA"),
                r#use: String::from("sig"),
                n: String::from(N),
                e: String::from(E),
                kid: String::from(KID),
                x5t: String::default(),
                x5c: Vec::default(),
            }],
        };

        let mut file = tempfile::NamedTempFile::new().unwrap();
        {
            let mut writer = BufWriter::new(&mut file);
            serde_json::to_writer(&mut writer, &jwks).unwrap();
        }

        test(file.path());
    }

    #[test]
    fn jwks_from_uri() {
        with_jwks(|path| {
            let jwks = Jwks::from_uri(&(String::from("file://") + path.to_str().unwrap())).unwrap();

            let expected_key = Key {
                alg: Algorithm::RS256,
                kty: String::from("RSA"),
                r#use: String::from("sig"),
                n: String::from(N),
                e: String::from(E),
                kid: String::from(KID),
                x5t: String::default(),
                x5c: Vec::default(),
            };
            assert_eq!(jwks.find(KID), Some(&expected_key));
            assert_eq!(jwks.find("spam"), None);
        });
    }

    #[test]
    fn jwks_from_uri_empty() {
        let mut file = tempfile::NamedTempFile::new().unwrap();
        {
            let mut writer = BufWriter::new(&mut file);
            serde_json::to_writer(&mut writer, &Jwks { keys: Vec::new() }).unwrap();
        }

        match Jwks::from_uri(&(String::from("file://") + file.path().to_str().unwrap())) {
            Err(Error::Configuration(msg)) => assert!(msg.contains("Jwks is empty")),
            _ => panic!("unexpected result"),
        };
    }

    #[test]
    fn jwks_from_uri_invalid_json() {
        let mut file = tempfile::NamedTempFile::new().unwrap();
        {
            let mut writer = BufWriter::new(&mut file);
            writer.write_all(b"[]").unwrap();
        }

        match Jwks::from_uri(&(String::from("file://") + file.path().to_str().unwrap())) {
            Err(Error::Configuration(msg)) => {
                assert!(msg.contains("Can't parse Jwks state as JSON"))
            }
            _ => panic!("unexpected result"),
        };
    }

    #[test]
    fn jwks_from_uri_invalid_uri() {
        match Jwks::from_uri("ftp://foo/bar") {
            Err(Error::Configuration(msg)) => assert!(msg.contains("URI is invalid")),
            _ => panic!("unexpected result"),
        };

        match Jwks::from_uri("http:/foo/bar") {
            Err(Error::Configuration(msg)) => assert!(msg.contains("URI is invalid")),
            _ => panic!("unexpected result"),
        };
    }

    #[test]
    fn jwks_from_uri_failed_load() {
        match Jwks::from_uri(&String::from("file://spam")) {
            Err(Error::Configuration(msg)) => assert!(msg.contains("Can't load Jwks state")),
            _ => panic!("unexpected result"),
        };
    }

    #[test]
    fn validate() {
        with_jwks(|path| {
            let validator = JwtValidator::new(
                AUDIENCE.to_string(),
                ISSUER.to_string(),
                &(String::from("file://") + path.to_str().unwrap()),
            )
            .unwrap();

            assert_eq!(
                validator.validate(USER_TOKEN).unwrap(),
                User::Authenticated {
                    name: String::from("user"),
                    permissions: Vec::new()
                }
            );
            match validator.validate(EXPIRED_TOKEN) {
                Err(Error::Validation(msg)) => assert!(msg.contains("ExpiredSignature")),
                _ => panic!("unexpected result"),
            };
            match validator.validate(INVALID_TOKEN) {
                Err(Error::Validation(msg)) => assert!(msg.contains("InvalidSignature")),
                _ => panic!("unexpected result"),
            };
            match validator.validate(INVALID_HEADER_TOKEN) {
                Err(Error::Input(msg)) => assert!(msg.contains("missing field `alg`")),
                _ => panic!("unexpected result"),
            };
            match validator.validate(NO_KID_TOKEN) {
                Err(Error::Input(msg)) => {
                    assert!(msg.contains("Token does not specify the key id"))
                }
                _ => panic!("unexpected result"),
            };
            match validator.validate(UNKNOWN_KID_TOKEN) {
                Err(Error::Configuration(msg)) => {
                    assert!(msg.contains("Signing key \"eggs\" can't be found"))
                }
                _ => panic!("unexpected result"),
            };
            match validator.validate(UNSUPPORTED_ALG_TOKEN) {
                Err(Error::Input(msg)) => {
                    assert!(msg.contains("Unsupported algorithm: HS256"))
                }
                _ => panic!("unexpected result"),
            };
        });
    }

    #[test]
    fn validate_invalid_params() {
        with_jwks(|path| {
            let validator = JwtValidator::new(
                "spam".to_string(),
                ISSUER.to_string(),
                &(String::from("file://") + path.to_str().unwrap()),
            )
            .unwrap();
            match validator.validate(USER_TOKEN) {
                Err(Error::Validation(msg)) => assert!(msg.contains("InvalidAudience")),
                _ => panic!("unexpected result"),
            };

            let validator = JwtValidator::new(
                AUDIENCE.to_string(),
                "eggs".to_string(),
                &(String::from("file://") + path.to_str().unwrap()),
            )
            .unwrap();
            match validator.validate(USER_TOKEN) {
                Err(Error::Validation(msg)) => assert!(msg.contains("InvalidIssuer")),
                _ => panic!("unexpected result"),
            };
        });
    }
}
