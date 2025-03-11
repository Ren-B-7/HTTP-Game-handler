use super::fen_parser::Gamestate;
use std::{io, str::FromStr};
use serde_json::from_str;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug)]
struct JsonInput {
    pub reason: String,
    pub fen: String,
    pub moves: String
}

#[derive(Debug)]
pub struct JsonOut {
    pub reason: String,
    pub state: Gamestate,
    pub moves: String
}

pub fn read_and_parse_input() -> Result<JsonOut, Box<dyn std::error::Error>> {
    let mut stdin: String = String::new();
    io::stdin().read_line(&mut stdin)?;

    let input: JsonInput = from_str(&stdin).unwrap();

    // Parse the FEN string into a Gamestate
    let state: Gamestate = if input.reason == "move" || input.reason == "validate" {
        Gamestate::from_str(&input.fen)?
    } else {
        Gamestate::from_str(&input.fen).unwrap_or_else(|_| Gamestate::new())
    };
    let moves: String = if input.reason == "move" {
        input.moves
    } else {
        String::new()
    };

    Ok(JsonOut {
        reason: input.reason,
        state,
        moves
    })
}
