/// Author: Renier Barnard
/// Converts a chess notation string (e.g. "e2") to an index pair (e.g. (1, 4)).
///
/// The returned `(row, col)` is 0-indexed, with the following layout:
pub fn chess_notation_to_index(notation: &str) -> Option<(usize, usize)> {
    if notation.len() != 2 {
        return None;
    }

    let mut chars = notation.chars();
    let file = chars.next().unwrap(); // Column (a-h)
    let rank = chars.next().unwrap(); // Row (1-8)

    if !('a'..='h').contains(&file) || !('1'..='8').contains(&rank) {
        return None;
    }

    let col: usize = (file as u8 - b'a') as usize; // 'a' -> 0, 'b' -> 1, ..., 'h' -> 7
    let row: usize = 8 - (rank as u8 - b'1') as usize - 1; // '8' -> 0, '7' -> 1, ..., '1' -> 7

    Some((row, col))
}

pub fn index_to_chess_notation(position: (u8, u8)) -> Option<String> {
    let (rank, file): (u8, u8) = position;

    if rank > 7 || file > 7 {
        return None;
    }

    Some(format!(
        "{}{}",
        (b'a' + file) as char,
        (b'0' + 8 - rank) as char
    ))
}
