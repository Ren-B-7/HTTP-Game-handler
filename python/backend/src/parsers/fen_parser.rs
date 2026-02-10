use serde::{Deserialize, Serialize};
use std::str::FromStr;

#[derive(Serialize, Deserialize, Debug)]
pub struct Gamestate {
    pub board: [[char; 8]; 8],
    pub player: char,
    pub castling: (char, char, char, char),
    pub enpassat: Option<(u8, u8)>,
    pub halfmove: u8,
    pub fullmove: u16,
}
impl Gamestate {
    pub fn new() -> Self {
        Gamestate {
            board: [[' '; 8]; 8],
            player: 'w',
            castling: ('-', '-', '-', '-'),
            enpassat: None,
            halfmove: 0,
            fullmove: 1,
        }
    }

    pub fn to_fen(self: &Self) -> String {
        let mut fen = String::new();
        for rank in 0usize..8 {
            let mut empty: u8 = 0;
            for file in 0usize..8 {
                match self.board[rank][file] {
                    ' ' => {
                        empty += 1;
                    }
                    _ => {
                        if empty > 0 {
                            fen.push_str(&empty.to_string());
                            empty = 0;
                        }
                        fen.push(self.board[rank][file]);
                    }
                }
            }
            if empty > 0 {
                fen.push_str(&empty.to_string());
            };
            if rank < 7 {
                fen.push('/');
            };
        }
        // Turn
        fen.push(' ');
        fen.push(self.player);

        // Castling rights
        fen.push(' ');
        let (wk, wq, bk, bq) = self.castling;
        let mut castling = String::new();
        if wk != '-' {
            castling.push('K');
        }
        if wq != '-' {
            castling.push('Q');
        }
        if bk != '-' {
            castling.push('k');
        }
        if bq != '-' {
            castling.push('q');
        }
        if castling.is_empty() {
            castling.push('-');
        }
        fen.push_str(&castling);

        // En passant target
        fen.push(' ');
        if let Some((row, file)) = self.enpassat {
            // Convert board coordinates (row, col) back to chess notation
            // row 0 = rank 8, row 7 = rank 1
            fen.push((b'a' + file) as char);
            fen.push((b'0' + (8 - row)) as char);
        } else {
            fen.push('-');
        }

        // Halfmove clock & Fullmove number
        fen.push(' ');
        fen.push_str(&self.halfmove.to_string());
        fen.push(' ');
        fen.push_str(&self.fullmove.to_string());

        fen
    }
}

impl FromStr for Gamestate {
    type Err = String;

    fn from_str(fen: &str) -> Result<Self, Self::Err> {
        let parts: Vec<&str> = fen.split_whitespace().collect();
        if parts.len() != 6 {
            return Err("Invalid FEN format".to_string());
        }

        let board: [[char; 8]; 8] = parse_board(parts[0])?;
        let player: char = parts[1].chars().next().ok_or("Invalid player turn")?;
        let castling: (char, char, char, char) = parse_castling(parts[2]);
        let enpassant: Option<(u8, u8)> = parse_enpassant(parts[3])?;
        let halfmove: u8 = parts[4]
            .parse::<u8>()
            .map_err(|_| "Invalid halfmove clock")?;
        let fullmove: u16 = parts[5]
            .parse::<u16>()
            .map_err(|_| "Invalid fullmove number")?;

        Ok(Gamestate {
            board,
            player,
            castling,
            enpassat: enpassant,
            halfmove,
            fullmove,
        })
    }
}

fn parse_board(board_str: &str) -> Result<[[char; 8]; 8], String> {
    let mut board: [[char; 8]; 8] = [[' '; 8]; 8];
    let rows: Vec<&str> = board_str.split('/').collect();

    if rows.len() != 8 {
        return Err("Invalid board format".to_string());
    }

    for (i, row) in rows.iter().enumerate() {
        let mut col = 0;
        // FEN starts from rank 8 (index 0 in FEN = row 0 in our board for black)
        // But notation.rs expects row 7 to be rank 1 (white's side)
        // So FEN rank 8 -> board[0], rank 1 -> board[7]
        let board_row = i;
        for c in row.chars() {
            if c.is_digit(10) {
                col += c.to_digit(10).unwrap() as usize;
            } else if "prnbqkPRNBQK".contains(c) {
                if col >= 8 {
                    return Err("Too many pieces in row".to_string());
                }
                board[board_row][col] = c;
                col += 1;
            } else {
                return Err("Invalid character in board".to_string());
            }
        }
        if col != 8 {
            return Err("Invalid row length".to_string());
        }
    }

    Ok(board)
}

fn parse_castling(castling_str: &str) -> (char, char, char, char) {
    let mut castling: (char, char, char, char) = ('-', '-', '-', '-');
    if castling_str != "-" {
        if castling_str.contains('K') {
            castling.0 = 'K';
        }
        if castling_str.contains('Q') {
            castling.1 = 'Q';
        }
        if castling_str.contains('k') {
            castling.2 = 'k';
        }
        if castling_str.contains('q') {
            castling.3 = 'q';
        }
    }
    castling
}

fn parse_enpassant(ep_str: &str) -> Result<Option<(u8, u8)>, String> {
    if ep_str == "-" {
        return Ok(None);
    }
    let chars: Vec<char> = ep_str.chars().collect();
    if chars.len() != 2 {
        return Err("Invalid en passant square".to_string());
    }
    
    // Convert chess notation to board coordinates
    // Example: "e3" -> file='e' (column 4), rank='3'
    // Board uses (row, col) where row 0 = rank 8, row 7 = rank 1
    let file: u8 = chars[0] as u8 - b'a';  // Column: a=0, b=1, ..., h=7
    let rank_num: u8 = chars[1].to_digit(10).ok_or("Invalid en passant rank")? as u8;
    
    if file > 7 || rank_num < 1 || rank_num > 8 {
        return Err("En passant square out of bounds".to_string());
    }
    
    // Convert rank number to row index: rank 8 -> row 0, rank 1 -> row 7
    let row: u8 = 8 - rank_num;
    
    Ok(Some((row, file)))
}
