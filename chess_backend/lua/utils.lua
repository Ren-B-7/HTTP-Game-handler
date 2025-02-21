Exists, Json = pcall(require, "json")
if not (Exists and Json) then
	Base.error("JSON library not found", 0)
	return
end

Base = {}

Base.FEN_INIT = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

Base.error_levels = {
	"Fatal",
	"Error",
	"Warning",
	"Info",
	"Debug",
}

---Converts message to error with desired level
---@param msg string
---@param level number
Base.error = function(msg, level)
	if type(msg) ~= "string" then
		return
	end
	if type(level) ~= "number" then
		level = 1
	end
	if level <= -1 then
		return print(Json.encode({ test = msg }))
	end
	if level == 0 then
		level = 1
	elseif level > 5 then
		level = 5
	end

	print(Json.encode({ error = "[" .. Base.error_levels[level] .. "] - " .. msg }))
end
---Converts given string to a table of FEN values if it is valid, else prints error to stdout (STILL NEED TO WORK ON TERMINATION)
---@param fen string
Base.fen_to_table = function(fen)
	-- Extract required fields directly instead of looping with regex
	if type(fen) ~= "string" then
		return Base.error("Invalid FEN: Must be a string", 0)
	end
	local board_fen, turn, castling, en_passant, halfmove, fullmove =
		fen:match("^(%S+)%s+(%S+)%s+(%S+)%s+(%S+)%s+(%S+)%s+(%S+)")

	-- Ensure all fields exist
	if not (board_fen and turn and castling and en_passant and halfmove and fullmove) then
		Base.error("Invalid FEN: Missing fields", 1)
	end

	-- Parse board
	local board, row_idx = {}, 1
	for rank in board_fen:gmatch("[^/]+") do
		if row_idx > 8 then
			Base.error("Invalid FEN: Too many ranks", 1)
		end

		board[row_idx] = {}
		local col_idx, square_count = 1, 0

		for char in rank:gmatch(".") do
			if char:match("%d") then
				local empty_spaces = tonumber(char)
				for _ = 1, empty_spaces do
					board[row_idx][col_idx] = " " -- Empty square
					col_idx = col_idx + 1
					square_count = square_count + 1
				end
			elseif char:match("[rnbqkpRNBQKP]") then
				board[row_idx][col_idx] = char -- Piece character
				col_idx = col_idx + 1
				square_count = square_count + 1
			else
				Base.error("Invalid FEN: Unexpected character in board description: " .. char, 1)
			end
		end

		if square_count ~= 8 then
			Base.error("Invalid FEN: Rank " .. row_idx .. " does not have exactly 8 squares", 1)
		end

		row_idx = row_idx + 1
	end
	if row_idx ~= 9 then
		Base.error("Invalid FEN: Board must have exactly 8 ranks", 1)
	end

	-- Convert numeric fields to numbers
	halfmove, fullmove = math.floor(tonumber(halfmove)), math.floor(tonumber(fullmove))
	if not (halfmove and fullmove) then
		Base.error("Invalid FEN: Halfmove/fullmove counters must be numbers", 3)
	end

	return {
		--- @type table<string, string> Board state
		board = board,
		--- @type string Player to move
		player = turn,
		--- @type string Castling rights
		castling = castling,
		--- @type string En passant square
		en_passant = en_passant,
		--- @type number Halfmove counter
		halfmove = halfmove,
		--- @type number Fullmove counter
		fullmove = fullmove,
	}
end
return Base
