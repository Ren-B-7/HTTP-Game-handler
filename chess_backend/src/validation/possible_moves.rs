use super::pieces::{bishop, king, knight, pawn, queen, rook};
use rayon::prelude::*;
use std::sync::{Arc, Mutex};

pub fn get_legal_moves(
    board: &[[char; 8]; 8],
    enpassat: (u8, u8),
    castling: (char, char, char, char),
    player: char,
) -> Vec<((u8, u8), (u8, u8))> {
    let king_position: Arc<Mutex<(u8, u8)>> = Arc::new(Mutex::new((10, 10))); // Shared king position

    // First pass: Locate the king
    (0usize..8).into_par_iter().for_each(|rank: usize| {
        (0usize..8).into_par_iter().for_each(|file: usize| {
            let piece: char = board[rank][file];
            if piece == ' ' || piece.is_uppercase() != (player == 'w') {
                return;
            }
            if piece.to_ascii_lowercase() == 'k' {
                *king_position.lock().unwrap() = (rank as u8, file as u8);
            }
        })
    });
    let king_position: (u8, u8) = Arc::try_unwrap(king_position)
        .unwrap()
        .into_inner()
        .unwrap();

    let attacking: Arc<Mutex<Vec<Vec<(u8, u8)>>>> = Arc::new(Mutex::new(Vec::new())); // Store attack paths
    let attacking_pieces: Arc<Mutex<Vec<(u8, u8)>>> = Arc::new(Mutex::new(Vec::new())); // Store attacking pieces
    let positions: Arc<Mutex<Vec<((u8, u8), (u8, u8))>>> = Arc::new(Mutex::new(Vec::new())); // Store all possible moves

    (0u8..8).into_par_iter().for_each(|rank| {
        (0u8..8).into_par_iter().for_each(|file| {
            let piece: char = board[rank as usize][file as usize];
            if piece == ' ' {
                return;
            }
            let from: (u8, u8) = (rank, file);

            let move_directions: Vec<Vec<(u8, u8)>> = match piece.to_ascii_lowercase() {
                'p' => pawn::get_possible_moves(from, board, enpassat),
                'r' => rook::get_possible_moves(from, board),
                'n' => knight::get_possible_moves(from, board),
                'b' => bishop::get_possible_moves(from, board),
                'q' => queen::get_possible_moves(from, board),
                'k' => king::get_possible_moves(from, board, castling),
                _ => return,
            };
            if piece.is_uppercase() != (player == 'w') {
                // Enemy piece: check if it attacks the king
                let attack_paths: Vec<Vec<(u8, u8)>> = move_directions
                    .iter()
                    .filter(|direction| direction.contains(&king_position))
                    .cloned()
                    .collect();

                if !attack_paths.is_empty() {
                    let mut att_lock: std::sync::MutexGuard<'_, Vec<Vec<(u8, u8)>>> =
                        attacking.lock().expect("Mutex poisoned");
                    let mut att_pieces_lock: std::sync::MutexGuard<'_, Vec<(u8, u8)>> =
                        attacking_pieces.lock().expect("Mutex poisoned");

                    att_lock.par_extend(attack_paths);
                    att_pieces_lock.push(from);
                }
                return; // Exit early since enemy pieces don't generate move positions
            }

            // Friendly piece: add to move list
            let mut pos_lock: std::sync::MutexGuard<'_, Vec<((u8, u8), (u8, u8))>> =
                positions.lock().expect("Mutex poisoned");
            pos_lock.extend(
                move_directions
                    .into_iter()
                    .flatten()
                    .map(|to: (u8, u8)| (from, to)),
            );
        });
    });

    // Convert Mutex-protected Vecs into normal Vecs
    let attacking: Vec<Vec<(u8, u8)>> = Arc::try_unwrap(attacking).unwrap().into_inner().unwrap();
    let attacking_pieces: Vec<(u8, u8)> = Arc::try_unwrap(attacking_pieces)
        .unwrap()
        .into_inner()
        .unwrap();
    let positions: Vec<((u8, u8), (u8, u8))> =
        Arc::try_unwrap(positions).unwrap().into_inner().unwrap();

    let in_check: bool = !attacking_pieces.is_empty();
    let double_check: bool = attacking_pieces.len() > 1;

    let filtered_moves: Vec<((u8, u8), (u8, u8))> = positions
        .into_par_iter()
        .filter(|&((from_x, from_y), (to_x, to_y)): &((u8, u8), (u8, u8))| {
            let from: (u8, u8) = (from_x, from_y);
            if from == king_position {
                // Ensure the king does not move into check
                let mut temp_board: [[char; 8]; 8] = *board;
                temp_board[to_x as usize][to_y as usize] =
                    temp_board[from_x as usize][from_y as usize];
                temp_board[from_x as usize][from_y as usize] = ' ';
                return !is_square_attacked((to_x, to_y), &temp_board, enpassat, player);
            }
            if in_check {
                if double_check {
                    return false; // King must move, other pieces can't block or capture
                }
                let is_in_attack: bool = attacking
                    .par_iter()
                    .any(|direction: &Vec<(u8, u8)>| direction.contains(&(to_x, to_y)));
                if let Some(&attacker) = attacking_pieces.first() {
                    return (to_x, to_y) == attacker || is_in_attack;
                }
                return false;
            }
            true
        })
        .collect();

    filtered_moves
}

fn is_square_attacked(
    pos: (u8, u8),
    board: &[[char; 8]; 8],
    enpassat: (u8, u8),
    player: char,
) -> bool {
    (0u8..8).into_par_iter().any(|rank: u8| -> bool {
        (0u8..8).into_par_iter().any(|file: u8| -> bool {
            let piece: char = board[rank as usize][file as usize];
            let from: (u8, u8) = (rank, file);
            if piece == ' ' || piece.is_uppercase() == (player == 'w') {
                return false;
            }

            let attack: Vec<Vec<(u8, u8)>> = match piece.to_ascii_lowercase() {
                'p' => pawn::get_possible_moves(from, board, enpassat),
                'r' => rook::get_possible_moves(from, board),
                'n' => knight::get_possible_moves(from, board),
                'b' => bishop::get_possible_moves(from, board),
                'q' => queen::get_possible_moves(from, board),
                'k' => king::get_possible_moves(from, board, (' ', ' ', ' ', ' ')),
                _ => return false,
            };

            attack
                .into_par_iter()
                .flatten()
                .any(|square: (u8, u8)| square == pos)
        })
    })
}
