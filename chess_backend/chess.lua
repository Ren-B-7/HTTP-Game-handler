local args, extern, test, file, verbose, cli = { ... }, {}, false, nil, 0, false
local root = debug.getinfo(1).source:match("^@(.*/)")

package.path = root and (root .. "lua/?.lua;" .. package.path) or package.path
root = nil

local ok, Utils = pcall(require, "utils")
if not ok then
	return error("Utils Library not found")
end

local Json
ok, Json = pcall(require, "json")
if not ok then
	return error("JSON library not found")
end

local Test
ok, Test = pcall(require, "tests")
if not ok then
	Utils.error("Test library not found", 4)
end

if not args[1] then
	args = { "-h" }
end

for i, v in pairs(args) do
	if v == "--help" or v == "-h" then
		print("Usage: lua chess.lua [-h] [-o [file]] [-n] [-v [0-4]] " .. (Test and " [-t]" or ""))
		print("commands:")
		print("\t -h \t --help \t: Prints this help message")
		print("\t -c \t --cli \t: To enable the JSP mode for cli usage")
		print("\t -o \t --output \t: Saves the output to a file")
		print("\t -n \t --no-print \t: Does not print to command line. For use with --output")
		if Test then
			print("\t -t \t --test \t: Runs the test suite")
		end
		print("\t -v \t --verbose \t: Uses more verbose messaging (0-4)")
		print("\t \t \t 4 - Debug \t 3 - Info \t 2 - Warning \t 1 - Error \t 0 - Fatal")
	elseif (v == "--test" or v == "-t") and Test then
		test = true
	elseif v == "--output" or v == "-o" then
		file = args[i + 1]
	elseif v == "--verbose" or v == "-v" then
		verbose = args[i + 1]
	elseif v == "--cli" or v == "-c" then
		cli = true
	end
end

if test and Test then
	Test.all()
else
	Test = nil
end

if cli then
	print("good")
	extern.main()
end

extern.main = function()
	collectgarbage()
	local out, json_input = {}, ""
	while true do
		out = {}
		::reiterate::
		local input = io.read()
		if input == "Ping" then
			print("Pong")
			goto reiterate
		end
		ok, json_input = pcall(Json.decode, input)
		if ok then
			if json_input["command"] == "init" then
				out = Utils.fen_to_table(Utils.FEN_INIT) or {}
			else
				out = Utils.fen_to_table(json_input["board"]) or {}
			end
			if not out then
				return Utils.error("Invalid FEN: " .. json_input["board"], 2)
			end
		else
			Utils.error("Invalid JSON: " .. json_input, 1)
		end
	end
end
