/*
* Author: Renier Barnard
*/
// todo!("Add unit tests")
// todo!("Add castling")
use rayon::prelude::*;

/// Calculates all possible moves for a king from a given position on the board.
///
/// This function determines the valid moves a king can make from its current
/// position, considering the standard chess rules for king movement. The king
/// can move one square in any direction (horizontally, vertically, or diagonally),
/// provided the destination square is either empty or occupied by an opponent's piece.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the king on the board (x, y).
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of characters.
///
/// # Returns
///
/// A vector of tuples where each tuple represents a valid position the king can move to.

pub fn get_possible_moves(
    from: (u8, u8),
    board: &[[char; 8]; 8],
    castling: (char, char, char, char),
) -> Vec<Vec<(u8, u8)>> {
    let (x, y): (u8, u8) = from;
    const BOARD_SIZE: u8 = 8;

    // All possible relative moves for a knight
    let possible_moves: [(i8, i8); 8] = [
        (0, 1),
        (0, -1),
        (1, 0),
        (-1, 0),
        (1, 1),
        (1, -1),
        (-1, 1),
        (-1, -1),
    ];

    let from_piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();

    possible_moves
        .into_par_iter() // Parallel iteration
        .filter_map(|(dx, dy): (i8, i8)| {
            let new_x: u8 = x.checked_add_signed(dx).unwrap_or(x);
            let new_y: u8 = y.checked_add_signed(dy).unwrap_or(y);

            // Ensure new_x and new_y are within bounds and non-negative before converting back to u8
            if new_x < BOARD_SIZE && new_y < BOARD_SIZE {
                let piece: char = board[new_x as usize][new_y as usize];

                // Allow capturing opposite color pieces or moving to an empty space

                if piece == ' ' || piece.is_uppercase() != from_piece_is_uppercase {
                    return Some(vec![(new_x, new_y)]);
                }
            }
            None
        })
        .collect()
}
