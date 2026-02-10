/*
Author: Renier Barnard
Performance Fix: Removed unnecessary parallelization for small iteration counts
*/

/// Calculates all possible moves for a rook from a given position on the board.
///
/// The function utilizes helper functions to determine all valid linear moves
/// in each direction (up, down, left, right) that the rook can make, taking into
/// account the current state of the board and any blocking pieces.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the rook on the board.
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of characters.
///
/// # Returns
///
/// A vector of vectors where each inner vector represents positions the rook can move to in one direction.

pub fn get_possible_moves(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<Vec<(u8, u8)>> {
    // PERFORMANCE FIX: Removed par_iter() - only 4 directions, overhead > benefit
    vec![
        check_move_rook_down(from, board),
        check_move_rook_up(from, board),
        check_move_rook_right(from, board),
        check_move_rook_left(from, board),
    ]
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rook_moves_center() {
        let mut board = [[' '; 8]; 8];
        board[4][4] = 'R'; // White rook at e4

        let moves = get_possible_moves((4, 4), &board);
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Rook should have 14 moves (4 up + 3 down + 4 left + 4 right - 1 for overlap)
        assert_eq!(all_moves.len(), 14);
    }

    #[test]
    fn test_rook_blocked_by_own_piece() {
        let mut board = [[' '; 8]; 8];
        board[4][4] = 'R'; // White rook at e4
        board[4][6] = 'P'; // White pawn at g4

        let moves = get_possible_moves((4, 4), &board);
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Should not include g4 or h4
        assert!(!all_moves.contains(&(4, 6)));
        assert!(!all_moves.contains(&(4, 7)));
        // Should include f4
        assert!(all_moves.contains(&(4, 5)));
    }

    #[test]
    fn test_rook_captures_enemy() {
        let mut board = [[' '; 8]; 8];
        board[4][4] = 'R'; // White rook at e4
        board[4][6] = 'p'; // Black pawn at g4

        let moves = get_possible_moves((4, 4), &board);
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Should include g4 (capture) but not h4
        assert!(all_moves.contains(&(4, 6)));
        assert!(!all_moves.contains(&(4, 7)));
    }
}
