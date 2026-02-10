use super::fen_parser::Gamestate;
use serde::{Deserialize, Serialize};
use serde_json::from_str;
use std::{io, str::FromStr};

#[derive(Serialize, Deserialize, Debug)]
struct JsonInput {
    pub reason: String,
    pub fen: String,
    pub moves: String,
}

#[derive(Debug)]
pub struct JsonIn {
    pub reason: String,
    pub state: Gamestate,
    pub moves: String,
}

pub fn read_and_parse_input() -> Result<JsonIn, Box<dyn std::error::Error>> {
    let mut stdin: String = String::new();
    io::stdin().read_line(&mut stdin)?;

    let input: JsonInput = from_str(&stdin).map_err(|e| Box::<dyn std::error::Error>::from(e))?;

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

    Ok(JsonIn {
        reason: input.reason,
        state,
        moves,
    })
}
