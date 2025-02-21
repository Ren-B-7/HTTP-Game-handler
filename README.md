# This is meant as a small test

Basically i want to bring a cli game handler to the web. To give the possibilities of having games against others with matchmaking, elo, logins and session handling

## The Python code

It is meant to serve the web front end. Handle connections and disconnections. Pass game states to and from backend to front-end.  
Also meant to do session handling, by tracking open tty sessions with the indicated game handlers

## Javascript, html, css

Basic, supposed to be the front end stack, where the javascript interacts with the python middle ware, where it will decide on actions. Like creating new users. Updating old user data. And other later functionality.  

## Lua/ RUST

Rust will be the absolute lowest level, where it does most of the checking in an async manner, but called async by the Lua wrapper. It will extend the lua wrapper using either the mLua/ hlua/ tlua library, decision to be made.  

Lua will essentially wrap the rust objects and be the main callee for the game handler.  
The idea is that the backend is a cli tool to determine legality/ actions that can/ will be allowed to be made.  

## Custom protocol

The "protocol" used will be a custom set, called jsp (Json Game protocol).  
It is a set way that messages between front, back and middle will look, to ensure extensibility of all parts of the project.  

## HEAVILY Subject to change
Asof the readme this project has been less than 1 week in development. Everything is subject to change.  
Recommendations will be appreciated.  

## Main Idea
Make the middle ware as extensible and distinct from the project as possible, such to increase reusability.


### Further notices
Files in static gets cached, files in non static gets sent on each request

# Todo


### Lua-Rust
Start Rust backend for the chess game
Finish lua cli for chess game

### Font end
Complete frontend for tha game page js/html/css

### Python
Finish requests and handlers in python for webserver
Debate on SSL encryption to enable https
