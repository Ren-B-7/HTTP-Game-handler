/*
Author: Renier Barnard
Performance Fix: Removed unnecessary parallelization
*/

/// Calculates all possible moves for a bishop from a given position on the board.
///
/// The function utilizes helper functions to determine all valid diagonal moves
/// in each direction (up-right, up-left, down-right, down-left) that the bishop can make,
/// taking into account the current state of the board and any blocking pieces.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the bishop on the board.
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of characters.
///
/// # Returns
///
/// A vector of vectors where each inner vector represents positions the bishop can move to in one direction.

pub fn get_possible_moves(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<Vec<(u8, u8)>> {
    // PERFORMANCE FIX: Removed par_iter() - only 4 directions, overhead > benefit
    vec![
        check_move_bishop_up_right(from, board),
        check_move_bishop_up_left(from, board),
        check_move_bishop_down_right(from, board),
        check_move_bishop_down_left(from, board),
    ]
}

/// Calculates all valid upward and rightward moves for a bishop from a given position on the board.
///
/// The bishop can move upwards and rightwards until it encounters another piece or the edge of the board.
/// It can capture an opponent's piece, but cannot move past it. This function will
/// return a vector of tuples representing the positions (x, y) the bishop can move to.
fn check_move_bishop_up_right(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
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

/// Calculates all valid upward and leftward moves for a bishop from a given position on the board.
///
/// The bishop can move upwards and leftwards until it encounters another piece or the edge of the board.
/// It can capture an opponent's piece, but cannot move past it. This function will
/// return a vector of tuples representing the positions (x, y) the bishop can move to.
fn check_move_bishop_up_left(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
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

/// Calculates all valid downward and rightward moves for a bishop from a given position on the board.
///
/// The bishop can move downwards and rightwards until it encounters another piece or the edge of the board.
/// It can capture an opponent's piece, but cannot move past it. This function will
/// return a vector of tuples representing the positions (x, y) the bishop can move to.
fn check_move_bishop_down_right(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
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

/// Calculates all valid downward and leftward moves for a bishop from a given position on the board.
///
/// The bishop can move downwards and leftwards until it encounters another piece or the edge of the board.
/// It can capture an opponent's piece, but cannot move past it. This function will
/// return a vector of tuples representing the positions (x, y) the bishop can move to.
fn check_move_bishop_down_left(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bishop_moves_center() {
        let mut board = [[' '; 8]; 8];
        board[4][4] = 'B'; // White bishop at e4

        let moves = get_possible_moves((4, 4), &board);
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Bishop should have 13 moves (4 diagonals)
        assert_eq!(all_moves.len(), 13);
    }

    #[test]
    fn test_bishop_blocked_by_own_piece() {
        let mut board = [[' '; 8]; 8];
        board[4][4] = 'B'; // White bishop at e4
        board[6][6] = 'P'; // White pawn at g2

        let moves = get_possible_moves((4, 4), &board);
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Should not include g2 or h1
        assert!(!all_moves.contains(&(6, 6)));
        assert!(!all_moves.contains(&(7, 7)));
        // Should include f3
        assert!(all_moves.contains(&(5, 5)));
    }

    #[test]
    fn test_bishop_captures_enemy() {
        let mut board = [[' '; 8]; 8];
        board[4][4] = 'B'; // White bishop at e4
        board[6][6] = 'p'; // Black pawn at g2

        let moves = get_possible_moves((4, 4), &board);
        let all_moves: Vec<(u8, u8)> = moves.into_iter().flatten().collect();
        
        // Should include g2 (capture) but not h1
        assert!(all_moves.contains(&(6, 6)));
        assert!(!all_moves.contains(&(7, 7)));
    }
}
