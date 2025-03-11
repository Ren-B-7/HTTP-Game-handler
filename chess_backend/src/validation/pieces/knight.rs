/*
* Author: Renier Barnard
*/
/// todo!("Add unit tests")
use rayon::prelude::*;

/// Returns all possible moves for a knight from a given position on the board.
///
/// This function takes a tuple representing the starting position of the knight as well
/// as a reference to the 8x8 chess board represented as a 2D array of characters.
/// It returns a vector of tuples representing the positions (x, y) the knight can move to.
///
/// The knight can move in an L-shape (two squares in one direction, then one square
/// to the side). The function will return all valid positions the knight can move to,
/// including capturing an opponent's piece, moving to an empty square, or moving to a square
/// occupied by a piece of the same color.
///
/// # Arguments
///
/// * `from` - A tuple representing the starting position of the knight (x, y).
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of characters.
///
/// # Returns
///
/// A vector of vectors, where each inner vector contains a tuple representing the position (x, y) the knight can move to.
pub fn get_possible_moves(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<Vec<(u8, u8)>> {
    const BOARD_SIZE: u8 = 8;
    let (x, y): (u8, u8) = from;

    let possible_moves: [(i8, i8); 8] = [
        (2, 1),
        (2, -1),
        (-2, 1),
        (-2, -1),
        (1, 2),
        (1, -2),
        (-1, 2),
        (-1, -2),
    ];

    let from_piece_is_uppercase = board[x as usize][y as usize].is_uppercase();

    possible_moves
        .into_par_iter()
        .filter_map(|(dx, dy): (i8, i8)| {
            let new_x: u8 = x.checked_add_signed(dx).unwrap_or(x);
            let new_y: u8 = y.checked_add_signed(dy).unwrap_or(y);

            // Ensure new_x and new_y are within bounds and non-negative before converting back to u8
            if new_x < BOARD_SIZE && new_y < BOARD_SIZE {
                let piece: char = board[new_x as usize][new_y as usize];

                if piece == ' ' || piece.is_uppercase() != from_piece_is_uppercase {
                    return Some(vec![(new_x, new_y)]);
                }
            }
            None
        })
        .collect()
}
