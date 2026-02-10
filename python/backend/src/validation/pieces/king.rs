/*
* Author: Renier Barnard
* Performance Fixes:
* - Removed unnecessary parallelization
* - Used const for king move offsets
* - Fixed: Castling implementation with proper validation
*/

// OPTIMIZATION: Use const instead of recreating array every call
const KING_OFFSETS: [(i8, i8); 8] = [
    (0, 1),
    (0, -1),
    (1, 0),
    (-1, 0),
    (1, 1),
    (1, -1),
    (-1, 1),
    (-1, -1),
];

/// Calculates all possible moves for a king from a given position on the board.
///
/// This function determines the valid moves a king can make from its current
/// position, considering the standard chess rules for king movement. The king
/// can move one square in any direction (horizontally, vertically, or diagonally),
/// provided the destination square is either empty or occupied by an opponent's piece.
///
/// Additionally handles castling moves when the king hasn't moved and castling
/// rights are available.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the king on the board (x, y).
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of characters.
/// * `castling` - A tuple of castling rights (white kingside, white queenside, black kingside, black queenside)
///
/// # Returns
///
/// A vector of vectors where each inner vector represents positions the king can move to in a direction.
/// The last vector in the result may contain castling moves.

pub fn get_possible_moves(
    from: (u8, u8),
    board: &[[char; 8]; 8],
    castling: (char, char, char, char),
) -> Vec<Vec<(u8, u8)>> {
    let (x, y): (u8, u8) = from;
    const BOARD_SIZE: u8 = 8;

    let from_piece_is_uppercase: bool = (board[x as usize][y as usize]).is_uppercase();

    // PERFORMANCE FIX: Removed par_iter() - only 8 positions, overhead > benefit
    let mut all_moves: Vec<Vec<(u8, u8)>> = KING_OFFSETS
        .iter()
        .filter_map(|&(dx, dy): &(i8, i8)| {
            let new_x: u8 = x.checked_add_signed(dx)?;
            let new_y: u8 = y.checked_add_signed(dy)?;

            if new_x < BOARD_SIZE && new_y < BOARD_SIZE {
                let piece: char = board[new_x as usize][new_y as usize];

                if piece == ' ' || piece.is_uppercase() != from_piece_is_uppercase {
                    return Some(vec![(new_x, new_y)]);
                }
            }
            None
        })
        .collect();

    // Check for castling moves and add them if valid
    let castling_moves = check_castle(board, from, castling);
    if !castling_moves.is_empty() {
        all_moves.push(castling_moves);
    }

    all_moves
}

/// Checks if a king can castle and returns valid castling moves.
///
/// Validates all FIDE chess rules for castling:
/// 1. King and rook haven't moved (checked via castling rights)
/// 2. Squares between king and rook are empty
/// 3. King is not currently in check (validated in possible_moves.rs)
/// 4. King does not pass through a square under attack (validated in possible_moves.rs)
/// 5. King does not end up in check (validated in possible_moves.rs)
///
/// # Arguments
///
/// * `board` - The current board state
/// * `from` - The king's current position (must be at starting position e1/e8)
/// * `castling` - Castling rights (K=white kingside, Q=white queenside, k=black kingside, q=black queenside)
///
/// # Returns
///
/// A vector of valid castling destination squares for the king
fn check_castle(
    board: &[[char; 8]; 8],
    from: (u8, u8),
    castling: (char, char, char, char),
) -> Vec<(u8, u8)> {
    let (x, y): (u8, u8) = from;
    
    // King must be at starting position (e1 for white = (7,4), e8 for black = (0,4))
    if !((x == 7 || x == 0) && y == 4) {
        return Vec::new();
    }

    let mut moves: Vec<(u8, u8)> = Vec::new();
    let piece: char = board[x as usize][y as usize];

    if piece == 'K' {
        // White castling from e1 (7,4)
        
        // Kingside (O-O): King moves e1->g1, rook moves h1->f1
        if castling.0 == 'K' 
            && board[7][5] == ' '  // f1 empty
            && board[7][6] == ' '  // g1 empty
            && board[7][7] == 'R'  // rook at h1
        {
            // Note: Validation that king doesn't pass through/into check
            // is handled in possible_moves.rs filter logic
            moves.push((7, 6));  // King to g1
        }
        
        // Queenside (O-O-O): King moves e1->c1, rook moves a1->d1
        if castling.1 == 'Q' 
            && board[7][1] == ' '  // b1 empty
            && board[7][2] == ' '  // c1 empty
            && board[7][3] == ' '  // d1 empty
            && board[7][0] == 'R'  // rook at a1
        {
            moves.push((7, 2));  // King to c1
        }
    } else if piece == 'k' {
        // Black castling from e8 (0,4)
        
        // Kingside (O-O): King moves e8->g8, rook moves h8->f8
        if castling.2 == 'k' 
            && board[0][5] == ' '  // f8 empty
            && board[0][6] == ' '  // g8 empty
            && board[0][7] == 'r'  // rook at h8
        {
            moves.push((0, 6));  // King to g8
        }
        
        // Queenside (O-O-O): King moves e8->c8, rook moves a8->d8
        if castling.3 == 'q' 
            && board[0][1] == ' '  // b8 empty
            && board[0][2] == ' '  // c8 empty
            && board[0][3] == ' '  // d8 empty
            && board[0][0] == 'r'  // rook at a8
        {
            moves.push((0, 2));  // King to c8
        }
    }

    moves
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_king_moves_center() {
        let mut board = [[' '; 8]; 8];
        board[4][4] = 'K'; // White king at e4

        let moves = get_possible_moves((4, 4), &board, ('-', '-', '-', '-'));
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // King should have 8 moves from center
        assert_eq!(all_moves.len(), 8);
    }

    #[test]
    fn test_king_moves_corner() {
        let mut board = [[' '; 8]; 8];
        board[0][0] = 'K'; // White king at a8

        let moves = get_possible_moves((0, 0), &board, ('-', '-', '-', '-'));
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // King should have 3 moves from corner
        assert_eq!(all_moves.len(), 3);
    }

    #[test]
    fn test_king_castling_kingside() {
        let mut board = [[' '; 8]; 8];
        board[7][4] = 'K'; // White king at e1
        board[7][7] = 'R'; // White rook at h1

        let moves = get_possible_moves((7, 4), &board, ('K', '-', '-', '-'));
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Should include castling move to g1
        assert!(all_moves.contains(&(7, 6)));
    }

    #[test]
    fn test_king_no_castling_blocked() {
        let mut board = [[' '; 8]; 8];
        board[7][4] = 'K'; // White king at e1
        board[7][7] = 'R'; // White rook at h1
        board[7][6] = 'N'; // Knight blocking at g1

        let moves = get_possible_moves((7, 4), &board, ('K', '-', '-', '-'));
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Should NOT include castling move (blocked)
        assert!(!all_moves.contains(&(7, 6)));
    }
}
