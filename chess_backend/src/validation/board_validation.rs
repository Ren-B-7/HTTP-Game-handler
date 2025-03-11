// Author: Renier Barnard

pub fn validate_board(board: &[[char; 8]; 8]) -> bool {
    let mut kings: (i8, i8) = (0, 0);
    let mut pawns: (i8, i8) = (0, 0);
    let mut queens: (i8, i8) = (0, 0);
    let mut knights: (i8, i8) = (0, 0);
    let mut rooks: (i8, i8) = (0, 0);
    let mut bishops: (i8, i8) = (0, 0);

    let player = |c: char| {
        if c.is_uppercase() {
            0 as i32
        } else {
            1 as i32
        }
    };

    // todo!("Add unit tests")
    for rank in 0..8 {
        for file in 0..8 {
            if [0, 7].contains(&rank) {
                if ['p', 'P'].contains(&board[rank][file]) {
                    panic!("Illegal pawn position: {:?}", (rank, file));
                }
            }
            // Increment according pieces
            match board[rank][file] {
                'p' | 'P' => match player(board[rank][file]) {
                    0 => pawns.0 += 1,
                    1 => pawns.1 += 1,
                    _ => panic!("Invalid player value"),
                },
                'r' | 'R' => match player(board[rank][file]) {
                    0 => rooks.0 += 1,
                    1 => rooks.1 += 1,
                    _ => panic!("Invalid player value"),
                },
                'n' | 'N' => match player(board[rank][file]) {
                    0 => knights.0 += 1,
                    1 => knights.1 += 1,
                    _ => panic!("Invalid player value"),
                },
                'b' | 'B' => match player(board[rank][file]) {
                    0 => bishops.0 += 1,
                    1 => bishops.1 += 1,
                    _ => panic!("Invalid player value"),
                },
                'q' | 'Q' => match player(board[rank][file]) {
                    0 => queens.0 += 1,
                    1 => queens.1 += 1,
                    _ => panic!("Invalid player value"),
                },
                'k' | 'K' => match player(board[rank][file]) {
                    0 => kings.0 += 1,
                    1 => kings.1 += 1,
                    _ => panic!("Invalid player value"),
                },
                _ => panic!("Unknown piece on the board: {}", board[rank][file]),
            }
        }
    }
    if !(kings.0 == 1 && kings.1 == 1) {
        panic!("Invalid number of kings: {} {}", kings.0, kings.1)
    }

    if !((0..=8).contains(&pawns.0) && (0..=8).contains(&pawns.1)) {
        panic!("Invalid number of pawns: {} {}", pawns.0, pawns.1)
    }

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
        panic!("Too many promoted pieces")
    }
    if promotable.1 < 0 {
        panic!("Too many promoted pieces")
    }
    return true;
}
