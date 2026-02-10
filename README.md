# Multi threaded python web server built for a chess game (i dont play chess)

Basically i want to bring a cli game handler to the web. To give the possibiliities of having games against others with matchmaking, elo, logins and session handling.

The draw-back? I want to refrain from using external libraries as much as possible.
Total external libraries used? 3... Serde json, rayon and chessboardv2, for rust, rust and javascript explicitly

## The Python code

It is meant to serve the web front end. Handle connections and disconnections. Pass game states to and from backend to front-end.  
Also meant to do session handling, by tracking open tty sessions with the indicated game handlers. I dubbed them engine instances.
The entire python and rust code is async and should run out of the box.

Has a configurable server.ini file for a config.
Config parser, code to setup the constants handler with queues and game states.

## Front end

The front end stack will have no frameworks, pure css, js and html for all operations, end points and communication.

## Rust  

The actual game logic will be handled in rust, here it will parse json objects passed on by python, parse them into Rust structs and execute the needed logic upon it.
In this case it parses the game and gets hands the parsed info back to the engine manager that sends it back to the js frontend. I use what i dubbed as the JSP. (Json game protocol) for running the rust backend

To build the code.
```rust
cd backend;
cargo build --release
```

## Main Idea

Make the middle ware as extensible and distinct from the project as possible, such to increase reusability.
Given any executable backend with any game.html and game.js with websockets any game can run successfully.

### Further notices
Files in the static/ directory gets cached, while non-static doesnt. All text files gets compressed with gzip.
All gzip objects gets cached into ram. To stop from overloading the cpu.

SSL is incorporated, but its without any gaurantees and without any promises.  
