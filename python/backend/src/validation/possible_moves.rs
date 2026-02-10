use super::pieces::{bishop, king, knight, pawn, queen, rook};
use rayon::prelude::*;

/// Determines the current game status after a move
pub enum GameStatus {
    Ongoing,
    Check,
    Checkmate,
    Stalemate,
}

pub fn get_legal_moves(
    board: &[[char; 8]; 8],
    enpassat: (u8, u8),
    castling: (char, char, char, char),
    player: char,
) -> Vec<((u8, u8), (u8, u8))> {
    // OPTIMIZATION: Parallel board scan (64 squares) - this is where Rayon helps
    // Collect everything in one parallel pass, then process sequentially
    let board_data: Vec<(u8, u8, char, Vec<Vec<(u8, u8)>>)> = (0u8..8)
        .into_par_iter()
        .flat_map(|rank| {
            (0u8..8).into_par_iter().filter_map(move |file| {
                let piece = board[rank as usize][file as usize];
                if piece == ' ' {
                    return None;
                }

                let from = (rank, file);
                let move_directions = match piece.to_ascii_lowercase() {
                    'p' => pawn::get_possible_moves(from, board, enpassat),
                    'r' => rook::get_possible_moves(from, board),
                    'n' => knight::get_possible_moves(from, board),
                    'b' => bishop::get_possible_moves(from, board),
                    'q' => queen::get_possible_moves(from, board),
                    'k' => king::get_possible_moves(from, board, castling),
                    _ => return None,
                };

                Some((rank, file, piece, move_directions))
            })
        })
        .collect();

    // Sequential processing (better for complex logic with branches)
    let mut king_position = (10u8, 10u8);
    let mut attacking_paths: Vec<(Vec<(u8, u8)>, (u8, u8))> = Vec::new();
    let mut positions: Vec<((u8, u8), (u8, u8))> = Vec::with_capacity(64);

    for (rank, file, piece, move_directions) in board_data {
        let from = (rank, file);

        // Find king
        if piece.to_ascii_lowercase() == 'k' && piece.is_uppercase() == (player == 'w') {
            king_position = from;
        }

        if piece.is_uppercase() != (player == 'w') {
            // Enemy piece: store all its attack directions for later king checking
            for direction in move_directions {
                if !direction.is_empty() {
                    attacking_paths.push((direction, from));
                }
            }
        } else {
            // Friendly piece: add all moves
            for direction in move_directions {
                for to in direction {
                    positions.push((from, to));
                }
            }
        }
    }

    // Filter attacking paths to only those that actually attack the king
    let mut actual_attacks: Vec<Vec<(u8, u8)>> = Vec::new();
    let mut actual_attackers: Vec<(u8, u8)> = Vec::new();
    
    for (path, attacker) in attacking_paths {
        if path.contains(&king_position) {
            actual_attacks.push(path);
            actual_attackers.push(attacker);
        }
    }

    let in_check = !actual_attackers.is_empty();
    let double_check = actual_attackers.len() > 1;

    // Filter moves for legality (sequential - complex branching logic)
    positions
        .into_iter()
        .filter(|&(from, to)| {
            if from == king_position {
                // Special handling for castling moves
                let is_castling = from.0 == to.0 && (from.1 as i8 - to.1 as i8).abs() == 2;

                if is_castling {
                    if in_check {
                        return false;
                    }

                    let is_kingside = to.1 > from.1;
                    let intermediate_y = if is_kingside { from.1 + 1 } else { from.1 - 1 };

                    if is_square_attacked((from.0, intermediate_y), board, enpassat, player) {
                        return false;
                    }
                }

                // King cannot move into check
                let mut temp_board = *board;
                temp_board[to.0 as usize][to.1 as usize] =
                    temp_board[from.0 as usize][from.1 as usize];
                temp_board[from.0 as usize][from.1 as usize] = ' ';
                return !is_square_attacked(to, &temp_board, enpassat, player);
            }

            if in_check {
                if double_check {
                    return false;
                }

                let is_in_attack_path = actual_attacks.iter().any(|path| path.contains(&to));
                if let Some(&attacker) = actual_attackers.first() {
                    return to == attacker || is_in_attack_path;
                }
                return false;
            }

            true
        })
        .collect()
}

/// Checks if the current player is in check
pub fn is_in_check(
    board: &[[char; 8]; 8],
    enpassat: (u8, u8),
    _castling: (char, char, char, char),
    player: char,
) -> bool {
    // Find the king (sequential - early exit optimization)
    let mut king_pos = None;
    for rank in 0u8..8 {
        for file in 0u8..8 {
            let piece = board[rank as usize][file as usize];
            if piece.to_ascii_lowercase() == 'k' && piece.is_uppercase() == (player == 'w') {
                king_pos = Some((rank, file));
                break;
            }
        }
        if king_pos.is_some() {
            break;
        }
    }

    if let Some(king_position) = king_pos {
        is_square_attacked(king_position, board, enpassat, player)
    } else {
        false
    }
}

/// Determines the game status for the current player
pub fn get_game_status(
    board: &[[char; 8]; 8],
    enpassat: (u8, u8),
    castling: (char, char, char, char),
    player: char,
) -> GameStatus {
    let legal_moves = get_legal_moves(board, enpassat, castling, player);
    let in_check = is_in_check(board, enpassat, castling, player);

    if legal_moves.is_empty() {
        if in_check {
            GameStatus::Checkmate
        } else {
            GameStatus::Stalemate
        }
    } else if in_check {
        GameStatus::Check
    } else {
        GameStatus::Ongoing
    }
}

// Sequential - can exit early when attack is found
fn is_square_attacked(
    pos: (u8, u8),
    board: &[[char; 8]; 8],
    enpassat: (u8, u8),
    player: char,
) -> bool {
    for rank in 0u8..8 {
        for file in 0u8..8 {
            let piece = board[rank as usize][file as usize];
            if piece == ' ' || piece.is_uppercase() == (player == 'w') {
                continue;
            }

            let from = (rank, file);
            let attack = match piece.to_ascii_lowercase() {
                'p' => pawn::get_possible_moves(from, board, enpassat),
                'r' => rook::get_possible_moves(from, board),
                'n' => knight::get_possible_moves(from, board),
                'b' => bishop::get_possible_moves(from, board),
                'q' => queen::get_possible_moves(from, board),
                'k' => king::get_possible_moves(from, board, (' ', ' ', ' ', ' ')),
                _ => continue,
            };

            for direction in attack {
                if direction.contains(&pos) {
                    return true;
                }
            }
        }
    }
    false
}
