use parsers::{
    fen_parser::Gamestate,
    notation::*,
    parse_error::*,
    parse_input::{read_and_parse_input, JsonIn},
    parse_output::*,
    pgn_parser::PgnGame,
};
use std::env;
use validation::board_validation::validate_board;
use validation::possible_moves::{get_game_status, get_legal_moves, is_in_check, GameStatus};

// Author: Renier Barnard
// Fixed: Added checkmate/stalemate detection and pawn promotion
// Additional fixes:
// - Fixed castling rights removal when rook is captured
// - Fixed en passant reset logic
// - Added 50-move rule draw detection
mod parsers;
mod validation;

fn cli() {
    loop {
        let input: JsonIn = match read_and_parse_input() {
            Ok(input) => input,
            Err(e) => {
                ParseError::new(&*e, &Gamestate::new()).print_stderr();
                continue;
            }
        };
        if input.reason == "exit" {
            break;
        }

        if input.reason == "ping" {
            println!("pong");
            continue;
        }

        let mut message: &str = "";
        let mut in_check = false;
        let mut checkmate = false;
        let mut stalemate = false;

        let mut game: Gamestate = input.state;
        if input.reason == "start" {
            message = "valid";
        } else if input.reason == "move" {
            let moves: ((u8, u8), (u8, u8)) = match input.moves.split_once('-') {
                Some((from, to)) => (
                    chess_notation_to_index(from).expect("Invalid move notation"),
                    chess_notation_to_index(to).expect("Invalid move notation"),
                ),
                None => ((0, 0), (0, 0)),
            };

            let enpassat: (u8, u8) = game.enpassat.unwrap_or((0, 0));

            // Calculate legal moves ONCE
            let legal_moves_before =
                get_legal_moves(&game.board, enpassat, game.castling, game.player);

            if legal_moves_before.contains(&moves) {
                let piece: char = game.board[moves.0 .0 as usize][moves.0 .1 as usize];
                let target: char = game.board[moves.1 .0 as usize][moves.1 .1 as usize];

                game.board[moves.1 .0 as usize][moves.1 .1 as usize] = piece;
                game.board[moves.0 .0 as usize][moves.0 .1 as usize] = ' ';

                // FIX: Reset en passant by default (will be set again if pawn double-move)
                game.enpassat = None;

                if piece.to_ascii_lowercase() == 'p' || target != ' ' {
                    game.halfmove = 0;
                } else {
                    game.halfmove += 1;
                }

                // Handle pawn-specific moves
                if piece.to_ascii_lowercase() == 'p' {
                    // Double move - set en passant square
                    if (moves.0 .0 as i8 - moves.1 .0 as i8).abs() == 2 {
                        game.enpassat = Some(((moves.0 .0 + moves.1 .0) / 2, moves.0 .1));
                    } else if moves.1 == enpassat {
                        // En passant capture - remove the captured pawn
                        game.board[moves.0 .0 as usize][moves.1 .1 as usize] = ' ';
                    }

                    // Pawn promotion - check if pawn reached opposite end
                    if moves.1 .0 == 0 || moves.1 .0 == 7 {
                        // Promote to Queen by default (can be extended to read from input.promotion)
                        game.board[moves.1 .0 as usize][moves.1 .1 as usize] =
                            if piece.is_uppercase() { 'Q' } else { 'q' };
                    }
                }

                // FIX: Remove castling rights if rook is captured
                if target == 'R' {
                    match moves.1 {
                        (7, 0) => game.castling.1 = '-', // White queenside rook captured
                        (7, 7) => game.castling.0 = '-', // White kingside rook captured
                        _ => (),
                    }
                } else if target == 'r' {
                    match moves.1 {
                        (0, 0) => game.castling.3 = '-', // Black queenside rook captured
                        (0, 7) => game.castling.2 = '-', // Black kingside rook captured
                        _ => (),
                    }
                }

                // Handle castling moves and update castling rights
                if piece == 'K' && moves.0 == (7, 4) {
                    game.castling.0 = '-';
                    game.castling.1 = '-';
                    match moves.1 {
                        (7, 6) => {
                            // Kingside castle: move rook
                            game.board[7][5] = game.board[7][7];
                            game.board[7][7] = ' ';
                        }
                        (7, 2) => {
                            // Queenside castle: move rook
                            game.board[7][3] = game.board[7][0];
                            game.board[7][0] = ' ';
                        }
                        _ => {}
                    }
                } else if piece == 'k' && moves.0 == (0, 4) {
                    game.castling.2 = '-';
                    game.castling.3 = '-';
                    match moves.1 {
                        (0, 6) => {
                            // Kingside castle: move rook
                            game.board[0][5] = game.board[0][7];
                            game.board[0][7] = ' ';
                        }
                        (0, 2) => {
                            // Queenside castle: move rook
                            game.board[0][3] = game.board[0][0];
                            game.board[0][0] = ' ';
                        }
                        _ => {}
                    }
                } else if piece == 'R' {
                    // White rook moved - update castling rights
                    match moves.0 {
                        (7, 0) => game.castling.1 = '-', // Queenside rook
                        (7, 7) => game.castling.0 = '-', // Kingside rook
                        _ => (),
                    };
                } else if piece == 'r' {
                    // Black rook moved - update castling rights
                    match moves.0 {
                        (0, 0) => game.castling.3 = '-', // Queenside rook
                        (0, 7) => game.castling.2 = '-', // Kingside rook
                        _ => (),
                    };
                };

                // Switch player
                game.player = if game.player == 'w' {
                    'b'
                } else {
                    game.fullmove += 1;
                    'w'
                };

                // FIX: Check for 50-move rule draw
                if game.halfmove >= 100 {
                    message = "draw by 50-move rule";
                    stalemate = true; // Use stalemate flag for draw
                } else {
                    // Check game status for the NEW player (who just got the turn)
                    let status = get_game_status(
                        &game.board,
                        game.enpassat.unwrap_or((0, 0)),
                        game.castling,
                        game.player,
                    );

                    match status {
                        GameStatus::Checkmate => {
                            message = "checkmate";
                            checkmate = true;
                        }
                        GameStatus::Stalemate => {
                            message = "stalemate";
                            stalemate = true;
                        }
                        GameStatus::Check => {
                            message = "check";
                            in_check = true;
                        }
                        GameStatus::Ongoing => {
                            message = "valid";
                        }
                    }
                }
            } else {
                ParseError::new(
                    std::io::Error::new(
                        std::io::ErrorKind::Other,
                        "Illegal move made, skipping move",
                    ),
                    &game,
                )
                .print_stderr();
                continue;
            }
        } else if input.reason == "validate" {
            match validate_board(&game.board) {
                Ok(_) => {
                    message = "valid";
                }
                Err(e) => {
                    ParseError::new(
                        std::io::Error::new(std::io::ErrorKind::Other, e),
                        &game,
                    )
                    .print_stderr();
                    continue;
                }
            }
        }

        let legal_moves: Vec<((u8, u8), (u8, u8))> = if input.reason == "validate"
            || (input.reason == "move" && message != "checkmate" && message != "stalemate" && message != "draw by 50-move rule")
        {
            get_legal_moves(
                &game.board,
                game.enpassat.unwrap_or((0, 0)),
                game.castling,
                game.player,
            )
        } else {
            Vec::new()
        };

        // Check if current player is in check (for status reporting)
        if !checkmate && !stalemate && input.reason != "start" {
            in_check = is_in_check(
                &game.board,
                game.enpassat.unwrap_or((0, 0)),
                game.castling,
                game.player,
            );
        }

        let legal_moves: Vec<String> = legal_moves
            .into_iter()
            .filter_map(|(x, y): ((u8, u8), (u8, u8))| {
                match (index_to_chess_notation(x), index_to_chess_notation(y)) {
                    (Some(from), Some(to)) => Some(format!("{}-{}", from, to)),
                    _ => None,
                }
            })
            .collect::<Vec<_>>();

        ParseOut::new(
            message.to_string(),
            &game,
            legal_moves,
            in_check,
            checkmate,
            stalemate,
        )
        .print_stdout();
    }
}

fn process_pgn(pgn_input: &str) -> Result<(), Box<dyn std::error::Error>> {
    // Try to parse as PGN
    let game = PgnGame::from_pgn(pgn_input)?;
    
    println!("PGN Game Parsed Successfully!");
    println!("==========================================");
    
    // Display headers
    if let Some(event) = game.get_header("Event") {
        println!("Event: {}", event);
    }
    if let Some(site) = game.get_header("Site") {
        println!("Site: {}", site);
    }
    if let Some(date) = game.get_header("Date") {
        println!("Date: {}", date);
    }
    if let Some(white) = game.get_header("White") {
        println!("White: {}", white);
    }
    if let Some(black) = game.get_header("Black") {
        println!("Black: {}", black);
    }
    println!("Result: {}", game.result);
    println!("==========================================");
    
    // Display moves
    println!("\nMoves ({} total):", game.moves.len());
    for (i, san_move) in game.moves.iter().enumerate() {
        let move_num = (i / 2) + 1;
        if i % 2 == 0 {
            print!("{}. {} ", move_num, san_move);
        } else {
            println!("{}", san_move);
        }
    }
    if game.moves.len() % 2 == 1 {
        println!(); // New line if odd number of moves
    }
    
    println!("\n==========================================");
    println!("PGN Output:");
    println!("{}", game.to_pgn());
    
    Ok(())
}

fn main() {
    let mut args: Vec<String> = env::args().collect();
    args.remove(0);
    if args.is_empty() {
        args.push("--help".to_string());
    }
    let mut file: String = String::new();
    let mut pgn_file: String = String::new();
    let mut pgn_string: String = String::new();
    let mut skip: bool = false;
    let (mut cli_mode, mut test, mut no_print, mut verbose): (bool, bool, bool, u8) =
        (false, false, false, 0);
    for v in args.iter() {
        if skip {
            skip = false;
            continue;
        }
        match v.as_str() {
            "--help" | "-h" => {
                println!("Usage: chess [options]");
                println!("commands:");
                println!("\t -h \t --help \t\t: Prints this help message: Default = true");
                println!(
                    "\t -c \t --cli \t\t: To enable the JSP mode for cli usage; Default = false"
                );
                println!("\t -o \t --output <file>\t: Saves the output to a file; Default = None");
                println!("\t -n \t --no-print \t\t: Does not print to command line. For use with --output; Default = false");
                println!("\t -t \t --test \t\t: Runs the test suite: Default = False");
                println!("\t -v \t --verbose <0-4>\t: Uses more verbose messaging (0-4): Default = 0");
                println!("\t \t \t\t  4 - Debug \t 3 - Info \t 2 - Warning \t 1 - Error \t 0 - Fatal");
                println!("\t -p \t --pgn <string>\t: Parse PGN string directly");
                println!("\t -f \t --pgn-file <file>\t: Read and parse PGN from file");
                println!("\nExamples:");
                println!("  chess --cli");
                println!("  chess --pgn-file game.pgn");
                println!("  chess --pgn '[Event \"Test\"] 1. e4 e5 2. Nf3'");
            }
            "--test" | "-t" => test = true,
            "--output" | "-o" => {
                skip = true;
                file = args[args.iter().position(|x: &String| x == v).unwrap() + 1].clone()
            }
            "--verbose" | "-v" => {
                skip = true;
                verbose = args[args.iter().position(|x: &String| x == v).unwrap() + 1]
                    .parse()
                    .unwrap()
            }
            "--pgn" | "-p" => {
                skip = true;
                pgn_string = args[args.iter().position(|x: &String| x == v).unwrap() + 1].clone()
            }
            "--pgn-file" | "-f" => {
                skip = true;
                pgn_file = args[args.iter().position(|x: &String| x == v).unwrap() + 1].clone()
            }
            "--cli" | "-c" => cli_mode = true,
            "--no-print" | "-n" => no_print = true,
            _ => (),
        }
    }
    
    // Process PGN if requested
    if !pgn_string.is_empty() {
        match process_pgn(&pgn_string) {
            Ok(_) => {},
            Err(e) => eprintln!("Error parsing PGN string: {}", e),
        }
        return;
    }
    
    if !pgn_file.is_empty() {
        match std::fs::read_to_string(&pgn_file) {
            Ok(content) => {
                match process_pgn(&content) {
                    Ok(_) => {},
                    Err(e) => eprintln!("Error parsing PGN file: {}", e),
                }
            },
            Err(e) => eprintln!("Error reading file '{}': {}", pgn_file, e),
        }
        return;
    }
    
    if test {}
    if file != "" {
        if no_print {}
    }
    if verbose > 0 {}
    if cli_mode {
        cli()
    }
}
