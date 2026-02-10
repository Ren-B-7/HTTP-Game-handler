// Author: Renier Barnard
// Performance optimization: Use const for starting ranks

const WHITE_PAWN_START_RANK: u8 = 6;
const BLACK_PAWN_START_RANK: u8 = 1;

/// Calculates all valid moves for a pawn from a given position on the board,
/// including initial double-step moves and captures.
///
/// The pawn can move forward to an empty square or capture an opponent's piece
/// diagonally. Additionally, pawns can move two squares forward from their
/// starting position. This function returns a vector of tuples representing
/// the positions (x, y) the pawn can move to.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the pawn on the board.
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of characters.
/// * `enpassat` - A tuple representing the en passant target square, if applicable.
///
/// # Returns
///
/// A vector of vectors where the first contains attack moves, second contains regular moves.
pub fn get_possible_moves(
    from: (u8, u8),
    board: &[[char; 8]; 8],
    enpassat: (u8, u8),
) -> Vec<Vec<(u8, u8)>> {
    let (x, y) = from;
    let from_piece_is_uppercase = board[x as usize][y as usize].is_uppercase();
    
    let mut positions_attack = Vec::with_capacity(2);
    let mut positions_regular = Vec::with_capacity(2);

    let new_x = if from_piece_is_uppercase {
        // White pawns move UP (row decreases)
        if x == 0 {
            return vec![positions_attack, positions_regular]; // Can't move off board
        }
        
        // Double move from starting position
        if x == WHITE_PAWN_START_RANK && board[(x - 2) as usize][y as usize] == ' ' {
            positions_regular.push((x - 2, y));
        }
        x - 1
    } else {
        // Black pawns move DOWN (row increases)
        if x == 7 {
            return vec![positions_attack, positions_regular]; // Can't move off board
        }
        
        // Double move from starting position
        if x == BLACK_PAWN_START_RANK && board[(x + 2) as usize][y as usize] == ' ' {
            positions_regular.push((x + 2, y));
        }
        x + 1
    };

    // Regular forward move
    if board[new_x as usize][y as usize] == ' ' {
        positions_regular.push((new_x, y));
    }

    // Diagonal captures (left)
    if y > 0 {
        let capture_pos = (new_x, y - 1);
        let target = board[new_x as usize][(y - 1) as usize];
        
        if target != ' ' && target.is_uppercase() != from_piece_is_uppercase {
            positions_attack.push(capture_pos);
        }
        
        // En passant left
        if capture_pos == enpassat {
            positions_attack.push(capture_pos);
        }
    }

    // Diagonal captures (right)
    if y < 7 {
        let capture_pos = (new_x, y + 1);
        let target = board[new_x as usize][(y + 1) as usize];
        
        if target != ' ' && target.is_uppercase() != from_piece_is_uppercase {
            positions_attack.push(capture_pos);
        }
        
        // En passant right
        if capture_pos == enpassat {
            positions_attack.push(capture_pos);
        }
    }

    vec![positions_attack, positions_regular]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_white_pawn_start() {
        let mut board = [[' '; 8]; 8];
        board[6][4] = 'P'; // White pawn at e2

        let moves = get_possible_moves((6, 4), &board, (0, 0));
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Should be able to move to e3 and e4
        assert!(all_moves.contains(&(5, 4)));
        assert!(all_moves.contains(&(4, 4)));
    }

    #[test]
    fn test_pawn_capture() {
        let mut board = [[' '; 8]; 8];
        board[4][4] = 'P'; // White pawn at e4
        board[3][3] = 'p'; // Black pawn at d5
        board[3][5] = 'p'; // Black pawn at f5

        let moves = get_possible_moves((4, 4), &board, (0, 0));
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Should capture both diagonal pawns
        assert!(all_moves.contains(&(3, 3)));
        assert!(all_moves.contains(&(3, 5)));
    }

    #[test]
    fn test_en_passant() {
        let mut board = [[' '; 8]; 8];
        board[3][4] = 'P'; // White pawn at e5
        
        let moves = get_possible_moves((3, 4), &board, (2, 5));
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Should include en passant square
        assert!(all_moves.contains(&(2, 5)));
    }
}
