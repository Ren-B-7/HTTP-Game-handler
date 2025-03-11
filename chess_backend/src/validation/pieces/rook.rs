/*
Author: Renier Barnard
*/
/// todo!("Add unit tests")
use rayon::prelude::*;

/// Calculates all possible moves for a rook from a given position on the board.
///
/// The function utilizes helper functions to determine all valid linear moves
/// in each direction (up, down, left, right) that the rook can make, taking into
/// account the current state of the board and any blocking pieces. The moves
/// are computed in parallel for efficiency.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the rook on the board.
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of characters.
///
/// # Returns
///
/// A vector of tuples where each tuple represents a valid position the rook can move to.

pub fn get_possible_moves(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<Vec<(u8, u8)>> {
    let move_fns: Vec<fn((u8, u8), &[[char; 8]; 8]) -> Vec<(u8, u8)>> = vec![
        check_move_rook_down,
        check_move_rook_up,
        check_move_rook_right,
        check_move_rook_left,
    ];

    move_fns
        .into_par_iter() // Parallel iterator
        .map(|f| f(from, board)) // Keep each direction separate
        .collect::<Vec<Vec<(u8, u8)>>>()
}

/// Gets all possible moves for a rook going up from a given position, given a board.
///
/// It takes a position (x, y) and a 2D array of characters representing the board.
/// It returns a vector of all possible moves the rook can make going up.
///
/// If the rook is not blocked, it will return all positions above the given position.
/// If the rook is blocked by a piece of the same color, it will not return that position.
/// If the rook is blocked by a piece of the opposite color, it will return that position.
fn check_move_rook_up(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
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

/// Gets all possible moves for a rook going down from a given position, given a board.
///
/// It takes a position (x, y) and a 2D array of characters representing the board.
/// It returns a vector of all possible moves the rook can make going down.
///
/// If the rook is not blocked, it will return all positions below the given position.
/// If the rook is blocked by a piece of the same color, it will not return that position.
/// If the rook is blocked by a piece of the opposite color, it will return that position.
fn check_move_rook_down(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
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

/// Gets all possible moves for a rook going left from a given position, given a board.
///
/// It takes a position (x, y) and a 2D array of characters representing the board.
/// It returns a vector of all possible moves the rook can make going left.
///
/// If the rook is not blocked, it will return all positions to the left of the given position.
/// If the rook is blocked by a piece of the same color, it will not return that position.
/// If the rook is blocked by a piece of the opposite color, it will return that position.
fn check_move_rook_left(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
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

/// Gets all possible moves for a rook going right from a given position, given a board.
///
/// It takes a position (x, y) and a 2D array of characters representing the board.
/// It returns a vector of all possible moves the rook can make going right.
///
/// If the rook is not blocked, it will return all positions to the right of the given position.
/// If the rook is blocked by a piece of the same color, it will not return that position.
/// If the rook is blocked by a piece of the opposite color, it will return that position.
fn check_move_rook_right(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
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
