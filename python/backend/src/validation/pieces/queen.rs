/**
 * Author: Renier Barnard
 * Performance Fix: Removed rayon - sequential is faster for only 8 directions
*/

/// Calculates all possible moves for a queen from a given position on the board.
///
/// The function utilizes helper functions to determine all valid linear moves
/// in each direction (up, down, left, right) as well as all valid diagonal moves
/// in each direction (up-right, up-left, down-right, down-left) that the queen can make,
/// taking into account the current state of the board and any blocking pieces.
///
/// # Arguments
///
/// * `from` - A tuple representing the current position of the queen on the board.
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of characters.
///
/// # Returns
///
/// A vector of vectors where each inner vector represents positions the queen can move to in one direction.
pub fn get_possible_moves(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<Vec<(u8, u8)>> {
    // PERFORMANCE FIX: Removed par_iter() - only 8 directions, overhead > benefit
    vec![
        check_move_queen_up(from, board),
        check_move_queen_down(from, board),
        check_move_queen_right(from, board),
        check_move_queen_left(from, board),
        check_move_queen_up_right(from, board),
        check_move_queen_up_left(from, board),
        check_move_queen_down_right(from, board),
        check_move_queen_down_left(from, board),
    ]
}

/// Calculates all valid upward and rightward moves for a queen from a given position on the board.
fn check_move_queen_up_right(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (mut x, mut y) = (from.0 as i8, from.1 as i8);
    let from_piece_is_uppercase = board[x as usize][y as usize].is_uppercase();

    while y > 0 && x < 7 {
        y -= 1;
        x += 1;
        let piece = board[x as usize][y as usize];
        if piece != ' ' {
            if piece.is_uppercase() != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break;
        }
        positions.push((x as u8, y as u8));
    }
    positions
}

/// Calculates all valid upward and leftward moves for a queen from a given position on the board.
fn check_move_queen_up_left(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (mut x, mut y) = (from.0 as i8, from.1 as i8);
    let from_piece_is_uppercase = board[x as usize][y as usize].is_uppercase();

    while y > 0 && x > 0 {
        y -= 1;
        x -= 1;
        let piece = board[x as usize][y as usize];
        if piece != ' ' {
            if piece.is_uppercase() != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break;
        }
        positions.push((x as u8, y as u8));
    }
    positions
}

/// Calculates all valid downward and rightward moves for a queen from a given position on the board.
fn check_move_queen_down_right(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (mut x, mut y) = (from.0 as i8, from.1 as i8);
    let from_piece_is_uppercase = board[x as usize][y as usize].is_uppercase();

    while y < 7 && x < 7 {
        y += 1;
        x += 1;
        let piece = board[x as usize][y as usize];
        if piece != ' ' {
            if piece.is_uppercase() != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break;
        }
        positions.push((x as u8, y as u8));
    }
    positions
}

/// Calculates all valid downward and leftward moves for a queen from a given position on the board.
fn check_move_queen_down_left(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (mut x, mut y) = (from.0 as i8, from.1 as i8);
    let from_piece_is_uppercase = board[x as usize][y as usize].is_uppercase();

    while y < 7 && x > 0 {
        y += 1;
        x -= 1;
        let piece = board[x as usize][y as usize];
        if piece != ' ' {
            if piece.is_uppercase() != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break;
        }
        positions.push((x as u8, y as u8));
    }
    positions
}

/// Calculates all valid upward moves for a queen from a given position on the board.
fn check_move_queen_up(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (x, mut y) = (from.0 as i8, from.1 as i8);
    let from_piece_is_uppercase = board[x as usize][y as usize].is_uppercase();

    while y > 0 {
        y -= 1;
        let piece = board[x as usize][y as usize];
        if piece != ' ' {
            if piece.is_uppercase() != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break;
        }
        positions.push((x as u8, y as u8));
    }
    positions
}

/// Calculates all valid downward moves for a queen from a given position on the board.
fn check_move_queen_down(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (x, mut y) = (from.0 as i8, from.1 as i8);
    let from_piece_is_uppercase = board[x as usize][y as usize].is_uppercase();

    while y < 7 {
        y += 1;
        let piece = board[x as usize][y as usize];
        if piece != ' ' {
            if piece.is_uppercase() != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break;
        }
        positions.push((x as u8, y as u8));
    }
    positions
}

/// Calculates all valid leftward moves for a queen from a given position on the board.
fn check_move_queen_left(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (mut x, y) = (from.0 as i8, from.1 as i8);
    let from_piece_is_uppercase = board[x as usize][y as usize].is_uppercase();

    while x > 0 {
        x -= 1;
        let piece = board[x as usize][y as usize];
        if piece != ' ' {
            if piece.is_uppercase() != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break;
        }
        positions.push((x as u8, y as u8));
    }
    positions
}

/// Calculates all valid rightward moves for a queen from a given position on the board.
fn check_move_queen_right(from: (u8, u8), board: &[[char; 8]; 8]) -> Vec<(u8, u8)> {
    let mut positions: Vec<(u8, u8)> = Vec::new();
    let (mut x, y) = (from.0 as i8, from.1 as i8);
    let from_piece_is_uppercase = board[x as usize][y as usize].is_uppercase();

    while x < 7 {
        x += 1;
        let piece = board[x as usize][y as usize];
        if piece != ' ' {
            if piece.is_uppercase() != from_piece_is_uppercase {
                positions.push((x as u8, y as u8));
            }
            break;
        }
        positions.push((x as u8, y as u8));
    }
    positions
}
