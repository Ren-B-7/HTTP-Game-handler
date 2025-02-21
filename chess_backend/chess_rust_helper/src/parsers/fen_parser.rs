use mlua::{Lua, Result, Table, Value, Error};

struct Base;

impl Base {

    /// Constructs a runtime error with the given message and error code.
    ///
    /// # Arguments
    ///
    /// * `message` - A string slice that holds the error message.
    /// * `code` - An integer representing the error code.
    ///
    /// # Returns
    ///
    /// * A `Result<Value>` containing a runtime error with the formatted message.
    fn error<T>(message: &str, code: i32) -> Result<T, mlua::Error> {
        Err(mlua::Error::RuntimeError(format!("Error {}: {}", code, message)))
    }


    /// Converts given string to a table of FEN values if it is valid, else prints error to stdout (STILL NEED TO WORK ON TERMINATION)
    ///
    /// # Arguments
    ///
    /// * `lua` - The Lua runtime to use to create the table
    /// * `fen` - A string slice that holds the FEN to parse
    ///
    /// # Returns
    ///
    /// * A `Result<Table>` containing the parsed FEN, or an error if the FEN is invalid
    fn fen_to_table(lua: &Lua, fen: &str) -> Result<Table> {
        if !fen.is_ascii() {
            return Self::error("Invalid FEN: Must be an ASCII string", 0);
        }

        let parts: Vec<&str> = fen.split_whitespace().collect();
        if parts.len() != 6 {
            return Self::error("Invalid FEN: Missing fields", 1);
        }

        let board_fen = parts[0];
        let turn = parts[1];
        let castling = parts[2];
        let en_passant = parts[3];

        let halfmove = parts[4].parse::<i32>().map_err(|_| {
            mlua::Error::RuntimeError("Invalid FEN: Halfmove counter must be a number".into())
        })?;

        let fullmove = parts[5].parse::<i32>().map_err(|_| {
            mlua::Error::RuntimeError("Invalid FEN: Fullmove counter must be a number".into())
        })?;

        let board = lua.create_table()?;
        for (row_idx, rank) in board_fen.split('/').enumerate() {
            let row = lua.create_table()?;
            let mut col_idx = 1;

            for ch in rank.chars() {
                if ch.is_digit(10) {
                    let empty_spaces = ch.to_digit(10).unwrap();
                    for _ in 0..empty_spaces {
                        row.set(col_idx, " ")?;
                        col_idx += 1;
                    }
                } else if "rnbqkpRNBQKP".contains(ch) {
                    row.set(col_idx, ch.to_string())?;
                    col_idx += 1;
                } else {
                    return Self::error(&format!("Invalid FEN: Unexpected character '{}'", ch), 1);
                }
            }

            if col_idx != 9 {
                return Self::error(&format!("Invalid FEN: Rank {} does not have exactly 8 squares", row_idx + 1), 1);
            }

            board.set(row_idx + 1, row)?;
        }

        let result = lua.create_table()?;
        result.set("board", board)?;
        result.set("player", turn)?;
        result.set("castling", castling)?;
        result.set("en_passant", en_passant)?;
        result.set("halfmove", halfmove)?;
        result.set("fullmove", fullmove)?;

        Ok(result)
    }
}
