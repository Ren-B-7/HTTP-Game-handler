// Author: Renier Barnard
// Fixed: Changed from panic to Result for better error handling

pub fn validate_board(board: &[[char; 8]; 8]) -> Result<(), String> {
    let mut kings: (i8, i8) = (0, 0);
    let mut pawns: (i8, i8) = (0, 0);
    let mut queens: (i8, i8) = (0, 0);
    let mut knights: (i8, i8) = (0, 0);
    let mut rooks: (i8, i8) = (0, 0);
    let mut bishops: (i8, i8) = (0, 0);

    let player = |c: char| {
        if c.is_uppercase() {
            0
        } else {
            1
        }
    };

    for rank in 0..8 {
        for file in 0..8 {
            // Check for illegal pawn positions (pawns can't be on ranks 1 or 8)
            if [0, 7].contains(&rank) {
                if ['p', 'P'].contains(&board[rank][file]) {
                    return Err(format!("Illegal pawn position at rank {} file {}", rank, file));
                }
            }
            
            // Count pieces
            match board[rank][file] {
                ' ' => continue,
                'p' | 'P' => match player(board[rank][file]) {
                    0 => pawns.0 += 1,
                    1 => pawns.1 += 1,
                    _ => return Err("Invalid player value".to_string()),
                },
                'r' | 'R' => match player(board[rank][file]) {
                    0 => rooks.0 += 1,
                    1 => rooks.1 += 1,
                    _ => return Err("Invalid player value".to_string()),
                },
                'n' | 'N' => match player(board[rank][file]) {
                    0 => knights.0 += 1,
                    1 => knights.1 += 1,
                    _ => return Err("Invalid player value".to_string()),
                },
                'b' | 'B' => match player(board[rank][file]) {
                    0 => bishops.0 += 1,
                    1 => bishops.1 += 1,
                    _ => return Err("Invalid player value".to_string()),
                },
                'q' | 'Q' => match player(board[rank][file]) {
                    0 => queens.0 += 1,
                    1 => queens.1 += 1,
                    _ => return Err("Invalid player value".to_string()),
                },
                'k' | 'K' => match player(board[rank][file]) {
                    0 => kings.0 += 1,
                    1 => kings.1 += 1,
                    _ => return Err("Invalid player value".to_string()),
                },
                c => return Err(format!("Unknown piece on the board: {}", c)),
            }
        }
    }

    // Validate king count
    if !(kings.0 == 1 && kings.1 == 1) {
        return Err(format!("Invalid number of kings: white={} black={}", kings.0, kings.1));
    }

    // Validate pawn count
    if !((0..=8).contains(&pawns.0) && (0..=8).contains(&pawns.1)) {
        return Err(format!("Invalid number of pawns: white={} black={}", pawns.0, pawns.1));
    }

    // Check for too many promoted pieces
    let mut promotable: (i8, i8) = (8 - pawns.0, 8 - pawns.1);

    for &(limit, ref counts) in &[(2, &rooks), (2, &knights), (2, &bishops), (1, &queens)] {
        if counts.0 > limit {
            promotable.0 = promotable.0.saturating_sub(counts.0 - limit);
        }
        if counts.1 > limit {
            promotable.1 = promotable.1.saturating_sub(counts.1 - limit);
        }
    }

    if promotable.0 < 0 {
        return Err("Too many promoted pieces for white".to_string());
    }
    if promotable.1 < 0 {
        return Err("Too many promoted pieces for black".to_string());
    }

    Ok(())
}
