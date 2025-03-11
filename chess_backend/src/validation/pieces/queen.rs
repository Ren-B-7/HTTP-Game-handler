/**
 * Author: Renier Barnard
*/
/// todo!("Add unit tests")
use rayon::prelude::*;

/// Calculates all possible moves for a queen from a given position on the board.
///
/// The function utilizes helper functions to determine all valid linear moves
/// in each direction (up, down, left, right) as well as all valid diagonal moves
/// in each direction (up-right, up-left, down-right, down-left) that the queen can make,
/// taking into account the current state of the board and any blocking pieces. The moves
/// are computed in parallel for efficiency.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the queen on the board.
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of characters.
///
/// # Returns
///
/// A vector of tuples where each tuple represents a valid position the queen can move to.
pub fn get_possible_moves(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<Vec<(u8, u8)>> {
    let move_fns: Vec<fn((u8, u8), &[[char; 8]; 8]) -> Vec<(u8, u8)>> = vec![
        check_move_queen_up,
        check_move_queen_down,
        check_move_queen_right,
        check_move_queen_left,
        check_move_queen_up_right,
        check_move_queen_up_left,
        check_move_queen_down_right,
        check_move_queen_down_left,
    ];

    move_fns
        .into_par_iter() // Parallel iterator
        .map(|f: fn((u8, u8), &[[char; 8]; 8]) -> Vec<(u8, u8)>| f(from, board)) // Runs each check function in parallel
        .collect()
}

/// Calculates all valid upward and rightward moves for a queen from a given position on the board.
///
/// The queen can move upwards and rightwards until it encounters another piece or the edge of the board.
/// It can capture an opponent's piece, but cannot move past it. This function will
/// return a vector of tuples representing the positions (x, y) the queen can move to.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the queen on the board.
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of bytes.
///
fn check_move_queen_up_right(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (mut x, mut y): (i8, i8) = (from.0 as i8, from.1 as i8);

    let from_piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();

    while y > 0 && x < 7 {
        y -= 1;
        x += 1;
        if (board[x as usize][y as usize]) != ' ' {
            let piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();
            if piece_is_uppercase != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break; // Stop if hitting any other piece
        }
        positions.push((x as u8, y as u8));
    }
    positions
}

/// Calculates all valid upward and leftward moves for a queen from a given position on the board.
///
/// The queen can move upwards and leftwards until it encounters another piece or the edge of the board.
/// It can capture an opponent's piece, but cannot move past it. This function will
/// return a vector of tuples representing the positions (x, y) the queen can move to.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the queen on the board.
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of bytes.
///
fn check_move_queen_up_left(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (mut x, mut y): (i8, i8) = (from.0 as i8, from.1 as i8);

    let from_piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();

    while y > 0 && x > 0 {
        y -= 1;
        x -= 1;
        if (board[x as usize][y as usize]) != ' ' {
            let piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();
            if piece_is_uppercase != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break; // Stop if hitting any other piece
        }
        positions.push((x as u8, y as u8));
    }
    positions
}

/// Calculates all valid downward and rightward moves for a queen from a given position on the board.
///
/// The queen can move downwards and rightwards until it encounters another piece or the edge of the board.
/// It can capture an opponent's piece, but cannot move past it. This function will
/// return a vector of tuples representing the positions (x, y) the queen can move to.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the queen on the board.
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of bytes.
///
fn check_move_queen_down_right(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (mut x, mut y): (i8, i8) = (from.0 as i8, from.1 as i8);

    let from_piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();

    while y < 7 && x < 7 {
        y += 1;
        x += 1;
        if (board[x as usize][y as usize]) != ' ' {
            let piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();
            if piece_is_uppercase != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break; // Stop if hitting any other piece
        }
        positions.push((x as u8, y as u8));
    }
    positions
}

/// Calculates all valid downward and leftward moves for a queen from a given position on the board.
///
/// The queen can move downwards and leftwards until it encounters another piece or the edge of the board.
/// It can capture an opponent's piece, but cannot move past it. This function will
/// return a vector of tuples representing the positions (x, y) the queen can move to.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the queen on the board.
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of bytes.
///
/// # Returns
///
/// A vector of tuples where each tuple represents a valid position the queen can move to.
fn check_move_queen_down_left(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (mut x, mut y): (i8, i8) = (from.0 as i8, from.1 as i8);

    let from_piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();

    while y < 7 && x > 0 {
        y += 1;
        x -= 1;
        if (board[x as usize][y as usize]) != ' ' {
            let piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();
            if piece_is_uppercase != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break; // Stop if hitting any other piece
        }
        positions.push((x as u8, y as u8));
    }
    positions
}

/// Calculates all valid upward moves for a queen from a given position on the board.
///
/// The queen can move upwards until it encounters another piece or the edge of the board.
/// It can capture an opponent's piece, but cannot move past it. This function will
/// return a vector of tuples representing the positions (x, y) the queen can move to.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the queen on the board.
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of bytes.
///
/// # Returns
///
/// A vector of tuples where each tuple represents a valid position the queen can move to.
fn check_move_queen_up(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (x, mut y): (i8, i8) = (from.0 as i8, from.1 as i8);

    let from_piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();

    while y > 0 {
        y -= 1;
        if (board[x as usize][y as usize]) != ' ' {
            let piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();
            if piece_is_uppercase != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break; // Stop if hitting any other piece
        }
        positions.push((x as u8, y as u8));
    }
    positions
}

/// Calculates all valid downward moves for a queen from a given position on the board.
///
/// The queen can move downwards until it encounters another piece or the edge of the board.
/// It can capture an opponent's piece, but cannot move past it. This function will
/// return a vector of tuples representing the positions (x, y) the queen can move to.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the queen on the board.
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of bytes.
///
/// # Returns
///
/// A vector of tuples where each tuple represents a valid position the queen can move to.
fn check_move_queen_down(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (x, mut y): (i8, i8) = (from.0 as i8, from.1 as i8);

    let from_piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();

    while y < 7 {
        y += 1;
        if (board[x as usize][y as usize]) != ' ' {
            let piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();
            if piece_is_uppercase != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break; // Stop if hitting any other piece
        }
        positions.push((x as u8, y as u8));
    }
    positions
}

/// Calculates all valid leftward moves for a queen from a given position on the board.
///
/// The queen can move leftwards until it encounters another piece or the edge of the board.
/// It can capture an opponent's piece, but cannot move past it. This function will
/// return a vector of tuples representing the positions (x, y) the queen can move to.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the queen on the board.
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of bytes.
///
/// # Returns
///
/// A vector of tuples where each tuple represents a valid position the queen can move to.
fn check_move_queen_left(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (mut x, y): (i8, i8) = (from.0 as i8, from.1 as i8);

    let from_piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();

    while x > 0 {
        x -= 1;
        if (board[x as usize][y as usize]) != ' ' {
            let piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();
            if piece_is_uppercase != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break; // Stop if hitting any other piece
        }
        positions.push((x as u8, y as u8));
    }
    positions
}

/// Calculates all valid rightward moves for a queen from a given position on the board.
///
/// The queen can move rightwards until it encounters another piece or the edge of the board.
/// It can capture an opponent's piece, but cannot move past it. This function will
/// return a vector of tuples representing the positions (x, y) the queen can move to.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the queen on the board.
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of bytes.
///
/// # Returns
///
/// A vector of tuples where each tuple represents a valid position the queen can move to.
fn check_move_queen_right(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (mut x, y): (i8, i8) = (from.0 as i8, from.1 as i8);

    let from_piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();

    while x < 7 {
        x += 1;
        if (board[x as usize][y as usize]) != ' ' {
            let piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();
            if piece_is_uppercase != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break; // Stop if hitting any other piece
        }
        positions.push((x as u8, y as u8));
    }
    positions
}
