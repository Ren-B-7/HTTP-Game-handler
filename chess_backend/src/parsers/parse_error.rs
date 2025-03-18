use super::fen_parser::Gamestate;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::error::Error;
use std::fmt;

#[derive(Serialize, Deserialize, Debug)]
pub struct ParseError {
    error: String,
    fen: String,
}

impl ParseError {
    pub fn new<E: Error>(error: E, game_state: &Gamestate) -> Self {
        Self {
            error: error.to_string(),
            fen: Gamestate::to_fen(game_state),
        }
    }

    pub fn to_json(&self) -> Value {
        json!({
            "error": self.error,
            "fen": self.fen
        })
    }

    pub fn print_stdout(&self) {
        println!("{}", self.to_json());
    }

    pub fn print_stderr(&self) {
        eprintln!("{}", self.to_json());
    }
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "ParseError: {}", self.error)
    }
}

/// Implements `std::error::Error`
impl Error for ParseError {}
