use super::fen_parser::Gamestate;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::fmt;

#[derive(Serialize, Deserialize, Debug)]
pub struct ParseOut {
    message: String,
    fen: String,
    possible_moves: Vec<String>,
    in_check: bool,
    checkmate: bool,
    stalemate: bool,
    game_over: bool,
}

impl ParseOut {
    pub fn new(
        message: String,
        game_state: &Gamestate,
        possible_moves: Vec<String>,
        in_check: bool,
        checkmate: bool,
        stalemate: bool,
    ) -> Self {
        Self {
            message: String::from(message),
            fen: Gamestate::to_fen(game_state),
            possible_moves,
            in_check,
            checkmate,
            stalemate,
            game_over: checkmate || stalemate,
        }
    }

    pub fn to_json(&self) -> Value {
        json!({
            "message": self.message,
            "fen": self.fen,
            "possible_moves": self.possible_moves,
            "in_check": self.in_check,
            "checkmate": self.checkmate,
            "stalemate": self.stalemate,
            "game_over": self.game_over
        })
    }

    pub fn print_stdout(&self) {
        println!("{}", self.to_json());
    }
}

impl fmt::Display for ParseOut {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "ParseOut: {}", self.message)
    }
}
