use serde::{Serialize, Serializer};

type ChronoUtc = chrono::DateTime<chrono::Utc>;

/// A wrapper around DateTime<Utc> from chrono that allows us
/// to implement Serialize (otherwise, Rust forbids implementing
/// a foreign trait for a foreign type from a different crate).
#[derive(Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct DateTime(ChronoUtc);

impl From<ChronoUtc> for DateTime {
    fn from(value: ChronoUtc) -> Self {
        Self(value)
    }
}
impl From<DateTime> for ChronoUtc {
    fn from(value: DateTime) -> Self {
        value.0
    }
}

impl Serialize for DateTime {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(&self.0.to_rfc3339())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_datetime_from() {
        let reference = chrono::DateTime::parse_from_rfc3339("2020-08-09T10:39:57+00:00")
            .unwrap()
            .with_timezone(&chrono::Utc);

        // from() conversions work in both directions: chrono::DateTime --> DateTime
        let dt = DateTime::from(reference);
        assert_eq!(dt.0, reference);

        // and DateTime --> chrono::DateTime
        let chrono_dt = chrono::DateTime::from(dt);
        assert_eq!(chrono_dt, reference);
    }

    #[test]
    fn test_datetime_serialize() {
        let reference = chrono::DateTime::parse_from_rfc3339("2020-08-09T10:39:57+00:00")
            .unwrap()
            .with_timezone(&chrono::Utc);

        let dt = DateTime::from(reference);

        // DateTime is serialized to its string representation (JSON strings are
        // enclosed in double quotes)
        let expected = "\"2020-08-09T10:39:57+00:00\"";
        let actual = serde_json::to_string(&dt).expect("failed to serilize DateTime");
        assert_eq!(actual, expected);
    }
}
