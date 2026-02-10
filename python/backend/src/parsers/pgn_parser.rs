/* Author: Renier Barnard
 * Fixed: Renamed from png_parser.rs to pgn_parser.rs
 * PGN = Portable Game Notation (standard chess game format)
 * PNG = Portable Network Graphics (image format - not relevant)
 * 
 * FIXES APPLIED:
 * - Fixed borrow-after-move error in from_pgn (lines 64-68)
 */

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Represents a complete PGN (Portable Game Notation) chess game
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct PgnGame {
    /// Game metadata tags (Event, Site, Date, Round, White, Black, Result, etc.)
    pub headers: HashMap<String, String>,
    /// List of moves in standard algebraic notation
    pub moves: Vec<String>,
    /// Game result: "1-0" (White wins), "0-1" (Black wins), "1/2-1/2" (Draw), "*" (Ongoing)
    pub result: String,
}

impl PgnGame {
    /// Creates a new empty PGN game
    pub fn new() -> Self {
        Self {
            headers: HashMap::new(),
            moves: Vec::new(),
            result: "*".to_string(),
        }
    }

    /// Parses a PGN string into a PgnGame struct
    ///
    /// # Example PGN Format:
    /// ```
    /// [Event "World Championship"]
    /// [Site "New York"]
    /// [Date "1972.07.11"]
    /// [Round "1"]
    /// [White "Fischer, Robert J."]
    /// [Black "Spassky, Boris V."]
    /// [Result "1-0"]
    ///
    /// 1. e4 e5 2. Nf3 Nc6 3. Bb5 1-0
    /// ```
    pub fn from_pgn(pgn_str: &str) -> Result<Self, String> {
        let mut game = PgnGame::new();
        let mut in_headers = true;
        let mut move_text = String::new();

        for line in pgn_str.lines() {
            let line = line.trim();

            // Skip empty lines
            if line.is_empty() {
                if in_headers {
                    in_headers = false; // Headers section ended
                }
                continue;
            }

            // Parse header tags [Key "Value"]
            if line.starts_with('[') && line.ends_with(']') {
                if let Some((key, value)) = parse_header_line(line) {
                    // FIX: Check key BEFORE moving values into insert
                    if key == "Result" {
                        game.result = value.clone();
                    }
                    game.headers.insert(key, value);
                }
            } else {
                // This is move text
                move_text.push_str(line);
                move_text.push(' ');
            }
        }

        // Parse the moves from the accumulated move text
        game.moves = parse_move_text(&move_text)?;

        // If no Result tag was found, try to extract from move text
        if game.result == "*" {
            if let Some(result) = extract_result_from_moves(&move_text) {
                game.result = result;
            }
        }

        Ok(game)
    }

    /// Converts the PGN game to a formatted string
    pub fn to_pgn(&self) -> String {
        let mut pgn = String::new();

        // Standard header order
        let ordered_headers = ["Event", "Site", "Date", "Round", "White", "Black", "Result"];

        // Write ordered headers first
        for header_name in &ordered_headers {
            if let Some(value) = self.headers.get(*header_name) {
                pgn.push_str(&format!("[{} \"{}\"]\n", header_name, value));
            }
        }

        // Write remaining headers (alphabetically)
        let mut other_headers: Vec<_> = self
            .headers
            .iter()
            .filter(|(k, _)| !ordered_headers.contains(&k.as_str()))
            .collect();
        other_headers.sort_by_key(|(k, _)| k.as_str());

        for (key, value) in other_headers {
            pgn.push_str(&format!("[{} \"{}\"]\n", key, value));
        }

        // Blank line between headers and moves
        pgn.push('\n');

        // Write moves (80 characters per line max)
        let mut line = String::new();
        for (i, move_san) in self.moves.iter().enumerate() {
            let move_num = (i / 2) + 1;
            let is_white = i % 2 == 0;

            let move_str = if is_white {
                format!("{}. {} ", move_num, move_san)
            } else {
                format!("{} ", move_san)
            };

            if line.len() + move_str.len() > 80 {
                pgn.push_str(&line);
                pgn.push('\n');
                line.clear();
            }

            line.push_str(&move_str);
        }

        // Add remaining moves and result
        if !line.is_empty() {
            pgn.push_str(&line);
        }
        pgn.push_str(&self.result);
        pgn.push('\n');

        pgn
    }

    /// Adds a move to the game in standard algebraic notation (SAN)
    pub fn add_move(&mut self, san_move: String) {
        self.moves.push(san_move);
    }

    /// Sets a header value
    pub fn set_header(&mut self, key: String, value: String) {
        self.headers.insert(key, value);
    }

    /// Gets a header value
    pub fn get_header(&self, key: &str) -> Option<&String> {
        self.headers.get(key)
    }
}

/// Parses a header line like [Event "World Championship"]
fn parse_header_line(line: &str) -> Option<(String, String)> {
    // Remove brackets
    let content = line.trim_matches(|c| c == '[' || c == ']').trim();

    // Find the first space (separates key from value)
    if let Some(space_pos) = content.find(' ') {
        let key = content[..space_pos].trim().to_string();
        let value_part = content[space_pos + 1..].trim();

        // Remove quotes from value
        let value = value_part.trim_matches('"').to_string();

        Some((key, value))
    } else {
        None
    }
}

/// Parses move text and extracts moves in standard algebraic notation
fn parse_move_text(text: &str) -> Result<Vec<String>, String> {
    let mut moves = Vec::new();
    let tokens: Vec<&str> = text.split_whitespace().collect();

    for token in tokens.iter() {
        let token = token.trim();

        // Skip empty tokens
        if token.is_empty() {
            continue;
        }

        // Skip move numbers (e.g., "1.", "2.", "10.")
        if token.ends_with('.') && token[..token.len() - 1].parse::<u32>().is_ok() {
            continue;
        }

        // Skip result indicators
        if matches!(token, "1-0" | "0-1" | "1/2-1/2" | "*") {
            continue;
        }

        // Skip comments (simplified - just skip text in {})
        if token.starts_with('{') {
            continue;
        }

        // Skip annotations like !!, !?, ??, etc.
        let clean_token = token.trim_end_matches(|c| "!?".contains(c));

        // This should be a move
        if !clean_token.is_empty() && is_valid_san_move(clean_token) {
            moves.push(clean_token.to_string());
        }
    }

    Ok(moves)
}

/// Basic validation for Standard Algebraic Notation moves
fn is_valid_san_move(san: &str) -> bool {
    // Castling
    if san == "O-O" || san == "O-O-O" {
        return true;
    }

    // Must have at least one character
    if san.is_empty() {
        return false;
    }

    // First character should be a piece (K, Q, R, B, N) or a file (a-h) for pawn moves
    let first_char = san.chars().next().unwrap();
    if !matches!(first_char, 'K' | 'Q' | 'R' | 'B' | 'N' | 'a'..='h') {
        return false;
    }

    // Should contain a file and rank somewhere (e.g., e4, Nf3, Qxd5)
    let has_file = san.chars().any(|c| matches!(c, 'a'..='h'));
    let has_rank = san.chars().any(|c| matches!(c, '1'..='8'));

    has_file && has_rank
}

/// Extracts game result from move text
fn extract_result_from_moves(text: &str) -> Option<String> {
    let tokens: Vec<&str> = text.split_whitespace().collect();
    for token in tokens.iter().rev() {
        if matches!(*token, "1-0" | "0-1" | "1/2-1/2" | "*") {
            return Some(token.to_string());
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_pgn() {
        let pgn_str = r#"
[Event "Test Game"]
[Site "Online"]
[Date "2026.02.08"]
[Round "1"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"#;

        let game = PgnGame::from_pgn(pgn_str).unwrap();
        assert_eq!(game.get_header("Event"), Some(&"Test Game".to_string()));
        assert_eq!(game.get_header("White"), Some(&"Player1".to_string()));
        assert_eq!(game.result, "1-0");
        assert!(game.moves.len() > 0);
    }

    #[test]
    fn test_to_pgn() {
        let mut game = PgnGame::new();
        game.set_header("Event".to_string(), "Test".to_string());
        game.set_header("White".to_string(), "Player1".to_string());
        game.set_header("Black".to_string(), "Player2".to_string());
        game.set_header("Result".to_string(), "1-0".to_string());
        game.add_move("e4".to_string());
        game.add_move("e5".to_string());
        game.result = "1-0".to_string();

        let pgn = game.to_pgn();
        assert!(pgn.contains("[Event \"Test\"]"));
        assert!(pgn.contains("1. e4 e5"));
    }
}
