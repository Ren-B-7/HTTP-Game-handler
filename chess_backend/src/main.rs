use std::env;
use parsers::fen_parser::Gamestate;
use parsers::parse_input::{JsonOut, read_and_parse_input};
use validation::board_validation::validate_board;
use parsers::notation::index_to_chess_notation;
use validation::possible_moves::get_legal_moves;

// Author: Renier Barnard
mod parsers;
mod validation;

fn cli() {
    loop {
        let input: JsonOut = match read_and_parse_input() {
            Ok(input) => {
                input
            },
            Err(e) => {
                println!("Error: {}", e);
                continue;
            }
        };
        if input.reason == "exit" {break;}

        if input.reason == "ping" {
            println!("pong");
            continue;
        }

        let game: Gamestate = input.state;
        if input.reason == "start" {
            
        } else if input.reason == "move" {
            
        } else if input.reason == "validate" {
            if validate_board(&game.board) {
                println!("Board is valid");
            }
        }

        let legal_moves: Vec<((u8, u8), (u8, u8))> =
            if input.reason == "validate" || input.reason == "move" {
                get_legal_moves(&game.board, game.enpassat.unwrap_or((0, 0)), game.castling, game.player)
            }
            else {
                Vec::new()
            };

        let legal_moves: Vec<(String, String)> = legal_moves
            .into_iter()
            .filter_map(|(x, y): ((u8, u8), (u8, u8))| {
                match (index_to_chess_notation(x), index_to_chess_notation(y)) {
                    (Some(from), Some(to)) => Some((from, to)),
                    _ => None,
                }
            })
            .collect::<Vec<_>>();
        println!("Legal moves: {:?}", legal_moves);
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
    let (mut cli_mode, mut test, mut no_print, mut verbose): (bool, bool, bool, u8) = (false, false, false, 0);
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
                println!("\t -c \t --cli \t: To enable the JSP mode for cli usage; Default = false");
                println!("\t -o \t --output \t: Saves the output to a file; Defualt = None");
                println!("\t -n \t --no-print \t: Does not print to command line. For use with --output; Default = false");
                println!("\t -t \t --test \t: Runs the test suite: Default = False");
                println!("\t -v \t --verbose \t: Uses more verbose messaging (0-4): Default = 0");
                println!("\t \t \t 4 - Debug \t 3 - Info \t 2 - Warning \t 1 - Error \t 0 - Fatal");
            }
            "--test" | "-t" => {
                test = true
            },
            "--output" | "-o" => {
                skip = true;
                file = args[args.iter().position(|x: &String| x == v).unwrap() + 1].clone()
            },
            "--verbose" | "-v" => {
                skip = true;
                verbose = args[args.iter().position(|x: &String| x == v).unwrap() + 1].parse().unwrap()
            },
            "--cli" | "-c" => {
                cli_mode = true
            },
            "--no-print" | "-n" => {
                no_print = true
            },
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
