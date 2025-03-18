// Author: Renier Barnard
// todo!("Add unit tests"

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
/// * `board` - A reference to the 8x8 chess board represented as a 2D array of characters.
/// * `enpassat` - A tuple representing the en passant target square, if applicable.
///
/// # Returns
///
/// A vector of tuples where each tuple represents a valid position the pawn can move to.

pub fn get_possible_moves(
    from: (u8, u8),
    board: &[[char; 8]; 8],
    enpassat: (u8, u8),
) -> Vec<Vec<(u8, u8)>> {
    fn add_pawn_move_regular(x: u8, y: u8, positions: &mut Vec<(u8, u8)>, board: &[[char; 8]; 8]) {
        if x < 8 && y < 8 {
            let piece: char = board[x as usize][y as usize];
            if piece == ' ' {
                positions.push((x, y));
            }
        }
    }
    fn add_pawn_move_capture(
        x: u8,
        y: u8,
        positions: &mut Vec<(u8, u8)>,
        board: &[[char; 8]; 8],
        from_piece_is_uppercase: bool,
    ) {
        if x < 8 && y < 8 {
            let piece: char = board[x as usize][y as usize];
            let piece_is_uppercase: bool = piece.is_uppercase();
            if piece != ' ' && piece_is_uppercase != from_piece_is_uppercase {
                positions.push((x, y));
            };
        }
    }
    let (x, y): (u8, u8) = from;
    let from_piece_is_uppercase: bool = board[x as usize][y as usize].is_uppercase();
    let mut positions_attack: Vec<(u8, u8)> = Vec::new();
    let mut positions_regular: Vec<(u8, u8)> = Vec::new();

    let mut new_x: u8 = x;

    if from_piece_is_uppercase {
        // White pawns move UP (-1)
        if x == 6 {
            add_pawn_move_regular(x - 2, y, &mut positions_regular, board);
        };
        if x > 0 {
            new_x = x - 1
        }
    } else {
        if x == 1 {
            add_pawn_move_regular(x + 2, y, &mut positions_regular, board);
        };
        if x < 7 {
            new_x = x + 1
        }
    };

    add_pawn_move_regular(new_x, y, &mut positions_regular, board);
    if y > 0 {
        add_pawn_move_capture(
            new_x,
            y - 1,
            &mut positions_attack,
            board,
            from_piece_is_uppercase,
        );
        if new_x == enpassat.0 {
            if y - 1 == enpassat.1 {
                positions_attack.push((new_x, y - 1))
            }
        }
    };
    if y < 7 {
        add_pawn_move_capture(
            new_x,
            y + 1,
            &mut positions_attack,
            board,
            from_piece_is_uppercase,
        );
        if new_x == enpassat.0 {
            if y + 1 == enpassat.1 {
                positions_attack.push((new_x, y + 1))
            }
        }
    };

    vec![positions_attack, positions_regular]
}
