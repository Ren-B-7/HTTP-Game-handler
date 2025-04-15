use parsers::{
    fen_parser::Gamestate,
    notation::*,
    parse_error::*,
    parse_input::{read_and_parse_input, JsonIn},
    parse_output::*,
};
use std::env;
use validation::board_validation::validate_board;
use validation::possible_moves::get_legal_moves;

// Author: Renier Barnard
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
            if get_legal_moves(&game.board, enpassat, game.castling, game.player).contains(&moves) {
                let piece: char = game.board[moves.0 .0 as usize][moves.0 .1 as usize];
                let target: char = game.board[moves.1 .0 as usize][moves.1 .1 as usize];

                game.board[moves.1 .0 as usize][moves.1 .1 as usize] = piece;
                game.board[moves.0 .0 as usize][moves.0 .1 as usize] = ' ';

                if piece.to_ascii_lowercase() == 'p' || target != ' ' {
                    game.halfmove = 0;
                } else {
                    game.halfmove += 1;
                }

                if piece.to_ascii_lowercase() == 'p' {
                    if (moves.0 .0 as i8 - moves.1 .0 as i8).abs() == 2 {
                        game.enpassat = Some(((moves.0 .0 + moves.1 .0) / 2, moves.0 .1));
                    } else if moves.1 == enpassat {
                        game.board[moves.0 .0 as usize][moves.1 .1 as usize] = ' ';
                    }
                } else {
                    game.enpassat = None;
                };

                if piece == 'K' && moves.0 == (7, 4) {
                    game.castling.0 = '-';
                    game.castling.1 = '-';
                    match moves.1 {
                        (7, 6) => {
                            game.board[7][5] = game.board[7][7];
                            game.board[7][7] = ' ';
                        }
                        (7, 2) => {
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
                            game.board[0][5] = game.board[0][7];
                            game.board[0][7] = ' ';
                        }
                        (0, 2) => {
                            game.board[0][3] = game.board[0][0];
                            game.board[0][0] = ' ';
                        }
                        _ => {}
                    }
                } else if piece == 'R' {
                    match moves.0 {
                        (7, 0) => game.castling.0 = '-',
                        (7, 7) => game.castling.1 = '-',
                        _ => (),
                    };
                } else if piece == 'r' {
                    match moves.0 {
                        (0, 0) => game.castling.2 = '-',
                        (0, 7) => game.castling.3 = '-',
                        _ => (),
                    };
                };
                game.player = if game.player == 'w' {
                    'b'
                } else {
                    game.fullmove += 1;
                    'w'
                };
                // Or check/ checkmate
                message = "valid";
            } else {
                ParseError::new(
                    std::io::Error::new(
                        std::io::ErrorKind::Other,
                        "Illegal move made, skipping move",
                    ),
                    &game,
                )
                .print_stderr();
            }
        } else if input.reason == "validate" {
            if !validate_board(&game.board) {
                ParseError::new(
                    std::io::Error::new(std::io::ErrorKind::Other, "Board not legal"),
                    &game,
                )
                .print_stderr();
                continue;
            }
            message = "valid";
        }

        let legal_moves: Vec<((u8, u8), (u8, u8))> =
            if input.reason == "validate" || input.reason == "move" {
                get_legal_moves(
                    &game.board,
                    game.enpassat.unwrap_or((0, 0)),
                    game.castling,
                    game.player,
                )
            } else {
                Vec::new()
            };

        let legal_moves: Vec<String> = legal_moves
            .into_iter()
            .filter_map(|(x, y): ((u8, u8), (u8, u8))| {
                match (index_to_chess_notation(x), index_to_chess_notation(y)) {
                    (Some(from), Some(to)) => Some(format!("{}-{}", from, to)),
                    _ => None,
                }
            })
            .collect::<Vec<_>>();
        ParseOut::new(message.to_string(), &game, legal_moves).print_stdout();
    }
}

fn main() {
    let mut args: Vec<String> = env::args().collect();
    args.remove(0);
    if args.is_empty() {
        args.push("--help".to_string());
    }
    let mut file: String = String::new();
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
                println!("\t -h \t --help \t: Prints this help message: Default = true");
                println!(
                    "\t -c \t --cli \t: To enable the JSP mode for cli usage; Default = false"
                );
                println!("\t -o \t --output \t: Saves the output to a file; Defualt = None");
                println!("\t -n \t --no-print \t: Does not print to command line. For use with --output; Default = false");
                println!("\t -t \t --test \t: Runs the test suite: Default = False");
                println!("\t -v \t --verbose \t: Uses more verbose messaging (0-4): Default = 0");
                println!("\t \t \t 4 - Debug \t 3 - Info \t 2 - Warning \t 1 - Error \t 0 - Fatal");
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
            "--cli" | "-c" => cli_mode = true,
            "--no-print" | "-n" => no_print = true,
            _ => (),
        }
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
