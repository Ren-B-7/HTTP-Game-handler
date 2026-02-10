/*
* Author: Renier Barnard
* Performance Fixes:
* - Removed unnecessary parallelization
* - Used const for knight move offsets
*/

// OPTIMIZATION: Use const instead of recreating array every call
const KNIGHT_OFFSETS: [(i8, i8); 8] = [
    (2, 1),
    (2, -1),
    (-2, 1),
    (-2, -1),
    (1, 2),
    (1, -2),
    (-1, 2),
    (-1, -2),
];

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

    let from_piece_is_uppercase = board[x as usize][y as usize].is_uppercase();

    // PERFORMANCE FIX: Removed par_iter() - only 8 positions, overhead > benefit
    // Changed to sequential iteration with filter_map
    KNIGHT_OFFSETS
        .iter()
        .filter_map(|&(dx, dy): &(i8, i8)| {
            let new_x: u8 = x.checked_add_signed(dx)?;
            let new_y: u8 = y.checked_add_signed(dy)?;

            // Ensure new_x and new_y are within bounds
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_knight_moves_center() {
        let mut board = [[' '; 8]; 8];
        board[4][4] = 'N'; // White knight at e4

        let moves = get_possible_moves((4, 4), &board);
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Knight should have 8 moves from center
        assert_eq!(all_moves.len(), 8);
    }

    #[test]
    fn test_knight_moves_corner() {
        let mut board = [[' '; 8]; 8];
        board[0][0] = 'N'; // White knight at a8

        let moves = get_possible_moves((0, 0), &board);
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Knight should have 2 moves from corner
        assert_eq!(all_moves.len(), 2);
        assert!(all_moves.contains(&(1, 2))); // b6
        assert!(all_moves.contains(&(2, 1))); // c7
    }

    #[test]
    fn test_knight_blocked_by_own_piece() {
        let mut board = [[' '; 8]; 8];
        board[4][4] = 'N'; // White knight at e4
        board[6][5] = 'P'; // White pawn at f2

        let moves = get_possible_moves((4, 4), &board);
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Should not include f2 (blocked by own pawn)
        assert!(!all_moves.contains(&(6, 5)));
        // Should have 7 moves (8 - 1 blocked)
        assert_eq!(all_moves.len(), 7);
    }

    #[test]
    fn test_knight_captures_enemy() {
        let mut board = [[' '; 8]; 8];
        board[4][4] = 'N'; // White knight at e4
        board[6][5] = 'p'; // Black pawn at f2

        let moves = get_possible_moves((4, 4), &board);
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Should include f2 (can capture enemy)
        assert!(all_moves.contains(&(6, 5)));
        assert_eq!(all_moves.len(), 8);
    }
}
