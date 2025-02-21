local test = {}

local ok, Utils = pcall(require, "utils")
if not ok then
	return error("Base Library not found")
end

local Json
ok, Json = pcall(require, "json")
if not ok then
	return error("No Json package found Skipping")
end

-- Function to capture print output
local function capture(func, ...)
	local old_print = print
	local output = {}

	print = function(...)
		table.insert(output, table.concat({ ... }, " "))
	end

	func(...)

	print = old_print
	return table.concat(output, "\n")
end

local function print_header(msg, count)
	print("")
	print("--------")
	print(msg .. " tests failed: " .. count)
	print("--------")
	print("")
end

local function compare_fen_tables(a, b)
	for i, v in ipairs(a) do
		if v ~= b[i] then
			return false
		end
	end
	return true
end

test.json_test_legal = function()
	if not Json then
		return print("No Json package found Skipping")
	end
	local failed_total, failed_count = 0, 0
	local tests_string, tests_lua =
		{
			'{"number": 100}',
			'{"string": "string"}',
			'{"float": 3.141592653}',
			'{"array": [0, 1, 2]}',
			'["a", "b", "c"]',
			"[1, 2, 3, 4]",
			'{"object": {"string": "string"}}',
			'{"object": {"number": 100}}',
			'{"object": {"float": 3.141592653}}',
			'{"object": {"object": {"array": ["0", "1", "2"]}}}',
		}, {
			{ ["s"] = "string" },
			{ ["i"] = 100 },
			{ ["f"] = 3.141592653 },
			{ ["a"] = { 0, 1, 2, 3, 4 } },
			{ ["o"] = { ["s"] = "string", ["i"] = 100, ["f"] = 3.14, ["o"] = { 1, 2, 3, 4 } } },
			{ ["bool"] = true },
			{ ["nested"] = { ["x"] = { ["y"] = { ["z"] = "deep value" } } } },
			{ ["mixed"] = { 42, "hello", { ["nested"] = { ["a"] = 1, ["b"] = 2 } } } },
			{ { 1, 2, 3, 4 } },
			{ { "a", "b", "c" } },
		}

	for i, t in ipairs(tests_string) do
		local ok, _ = pcall(Json.decode, t)
		if not ok then
			failed_count = failed_count + 1
			print("Decode failed at test [" .. i .. "]: " .. t)
		end
	end
	print("Decode failures: " .. tostring(failed_count))

	failed_total = failed_total + failed_count
	failed_count = 0

	for i, t in ipairs(tests_lua) do
		local ok, _ = pcall(Json.encode, t)
		if not ok then
			failed_count = failed_count + 1
			print("Encode failed at test [" .. i .. "]: " .. tostring(t))
		end
	end
	print("Encode failures: " .. tostring(failed_count))

	failed_total = failed_total + failed_count
	failed_count = 0

	for i, t in ipairs(tests_string) do
		local ok, encoded = pcall(Json.encode, Json.decode(t))
		if not ok then
			failed_count = failed_count + 1
			print("Round-trip (Decode -> Encode) failed at test [" .. i .. "]: " .. t)
		end
	end
	print("Decode-Encode failures: " .. tostring(failed_count))

	failed_total = failed_total + failed_count
	failed_count = 0

	for i, t in ipairs(tests_string) do
		-- First decode the JSON string to a Lua table
		local ok, decoded = pcall(Json.decode, t)
		if not ok then
			failed_count = failed_count + 1
			print("Decode step failed at test [" .. i .. "]: " .. t)
		else
			-- Re-encode and decode again to verify correctness
			ok, _ = pcall(Json.decode, Json.encode(decoded))
			if not ok then
				failed_count = failed_count + 1
				print("Re-encode -> Decode failed at test [" .. i .. "]: " .. Json.encode(decoded))
			end
		end
	end
	print("Encode-Decode failures: " .. tostring(failed_count))
	print("\n" .. "Total failed tests: " .. tostring(failed_total) .. "/" .. #tests_string * 2 + #tests_lua * 2 .. "\n")

	return failed_total
end

test.json_test_illegal = function()
	if not Json then
		return print("No Json package found Skipping")
	end
	local failed_total, failed_count = 0, 0
	local tests_string, tests_lua =
		{
			'{"number": 100', -- Missing closing brace
			'{"string": string}', -- Unquoted string value
			'{"float": 3.14.1592653}', -- Invalid number format
			'{"array": [0, 1, 2 3]}', -- Trailing comma in array
			'{"object": {"string": }"string"', -- Missing closing brace
			'{"object": {"number": 100, "extra":,}}', -- Invalid trailing comma
			'{"object": {"float": "3.141592653".}}', -- Extra dot
			'{"object": {"object": {"array": [0, 1, 2,,]}}}', -- Trailing comma in nested array
		}, {
			{ ["s"] = function() end }, -- Function values are not serializable
			{ ["i"] = coroutine.create(function() end) }, -- Coroutines are not serializable
			{ ["f"] = math.huge }, -- Infinity is not valid JSON
			{ ["a"] = { 0, 1, 2, nil, 4 } }, -- nil values in an array cause issues
			{ ["o"] = { ["s"] = "string", ["i"] = 100, ["f"] = 3.14, ["o"] = { 1, 2, nil, 4 } } }, -- nil in table
			{
				1,
				2,
				function()
					return nil
				end,
			}, -- Non-string table keys are not valid in JSON
			{ [{ ["nested"] = "table" }] = "bad key" }, -- Table as key (invalid for JSON)
			{ [{ ["nested"] = nil }] = "bad key" }, -- Table as key (invalid for JSON)
		}

	for i, t in ipairs(tests_string) do
		local ok, _ = pcall(Json.decode, t)
		if ok then
			failed_count = failed_count + 1
			print("Decode unexpectedly passed at test [" .. i .. "]: " .. t)
		end
	end
	print("Illegal decode failures: " .. tostring(failed_count))

	failed_total = failed_total + failed_count
	failed_count = 0

	for i, t in ipairs(tests_lua) do
		local ok, _ = pcall(Json.encode, t)
		if ok then
			failed_count = failed_count + 1
			print("Encode unexpectedly passed at test [" .. i .. "]: " .. tostring(t))
		end
	end
	print("Illegal encode failures: " .. tostring(failed_count))

	failed_total = failed_total + failed_count
	print("\n" .. "Total failed tests: " .. tostring(failed_total) .. "/" .. #tests_string + #tests_lua)

	return failed_total
end
test.utils_test_debug = function()
	if not Utils then
		return print("Dependancy Utils not found, skipping")
	end
	print("Starting Debug tests...")
	local failed, test_cases, counts =
		0, {
			{ msg = "Clamped min level", level = -10, expected = '{"test":"Clamped min level"}', type = "test" },
			{ msg = "Exact lower bound", level = -1, expected = '{"test":"Exact lower bound"}', type = "test" },
			{ msg = "Negative bounds", level = -2, expected = '{"test":"Negative bounds"}', type = "test" },
			{ msg = "Below range level", level = 0, expected = '{"error":"[Fatal] - Below range level"}', type = "fatal" },
			{ msg = "Something went wrong", level = 1, expected = '{"error":"[Fatal] - Something went wrong"}', type = "fatal" },
			{ msg = "String input", level = "2", expected = '{"error":"[Fatal] - String input"}', type = "fatal" },
			{ msg = "Critical failure", level = 2, expected = '{"error":"[Error] - Critical failure"}', type = "error" },
			{ msg = "I am a failure", level = 2, expected = '{"error":"[Error] - I am a failure"}', type = "error" },
			{ msg = "System crash", level = 3, expected = '{"error":"[Warning] - System crash"}', type = "warning" },
			{ msg = "Me", level = 3, expected = '{"error":"[Warning] - Me"}', type = "warning" },
			{ msg = "Right", level = 3, expected = '{"error":"[Warning] - Right"}', type = "warning" },
			{ msg = "Test", level = 4, expected = '{"error":"[Info] - Test"}', type = "info" },
			{ msg = "Pretty", level = 4, expected = '{"error":"[Info] - Pretty"}', type = "info" },
			{ msg = "Will", level = 4, expected = '{"error":"[Info] - Will"}', type = "info" },
			{ msg = "I", level = 4, expected = '{"error":"[Info] - I"}', type = "info" },
			{ msg = "Clamped max level", level = 5, expected = '{"error":"[Debug] - Clamped max level"}', type = "debug" },
			{ msg = "Exact upper bound", level = 5, expected = '{"error":"[Debug] - Exact upper bound"}', type = "debug" },
		}, { ["fatal"] = 0, ["error"] = 0, ["warning"] = 0, ["info"] = 0, ["debug"] = 0, ["test"] = 0 }

	for i, case in ipairs(test_cases) do
		local output = capture(Base.error, case.msg, case.level)
		if not (output == case.expected) then
			failed = failed + 1
			print("Test " .. i .. " FAILED: Expected " .. case.expected .. " but got " .. output)
			counts[case.type] = counts[case.type] + 1
		end
	end

	print("\nFail counts: ")
	for type, count in pairs(counts) do
		print(type .. ": " .. count)
	end
	print("\nTotal failed tests: " .. failed .. "/" .. #test_cases)

	return failed
end

test.fen_to_table_test = function()
	if not Utils then
		return print("Dependancy Utils not found, skipping")
	end
	print("Starting FEN -> Table tests...")
	-- error("Not implemented yet")
	local failed, test_cases =
		0, {
			{ cmd = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", passed = true, expected = {
				["fullmove"] = "1",
				["board"] = {
					{ "r", "n", "b", "q", "k", "b", "n", "r" },
					{ "p", "p", "p", "p", "p", "p", "p", "p" },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ "P", "P", "P", "P", "P", "P", "P", "P" },
					{ "R", "N", "B", "Q", "K", "B", "N", "R" },
				},
				["en_passant"] = "-",
				["castling"] = "KQkq",
				["player"] = "w",
				["halfmove"] = "0",
			} },
			{ cmd = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1", passed = true, expected = {
				["fullmove"] = "1",
				["board"] = {
					{ "r", "n", "b", "q", "k", "b", "n", "r" },
					{ "p", "p", "p", "p", "p", "p", "p", "p" },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", "P", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ "P", "P", "P", "P", " ", "P", "P", "P" },
					{ "R", "N", "B", "Q", "K", "B", "N", "R" },
				},
				["en_passant"] = "e3",
				["castling"] = "KQkq",
				["player"] = "b",
				["halfmove"] = "0",
			} },

			{ cmd = "rnbqkbnr/pppp1ppp/8/4p3/8/8/PPPPPPPP/RNBQKBNR w KQkq e6 0 2", passed = true, expected = {
				["fullmove"] = "2",
				["board"] = {
					{ "r", "n", "b", "q", "k", "b", "n", "r" },
					{ "p", "p", "p", "p", " ", "p", "p", "p" },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", "p", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ "P", "P", "P", "P", "P", "P", "P", "P" },
					{ "R", "N", "B", "Q", "K", "B", "N", "R" },
				},
				["en_passant"] = "e6",
				["castling"] = "KQkq",
				["player"] = "w",
				["halfmove"] = "0",
			} },

			{ cmd = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1", passed = true, expected = {
				["fullmove"] = "1",
				["board"] = {
					{ "r", "n", "b", "q", "k", "b", "n", "r" },
					{ "p", "p", "p", "p", "p", "p", "p", "p" },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ "P", "P", "P", "P", "P", "P", "P", "P" },
					{ "R", "N", "B", "Q", "K", "B", "N", "R" },
				},
				["en_passant"] = "-",
				["castling"] = "KQkq",
				["player"] = "b",
				["halfmove"] = "0",
			} },

			{ cmd = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", passed = true, expected = {
				["fullmove"] = "1",
				["board"] = {
					{ "r", "n", "b", "q", "k", "b", "n", "r" },
					{ "p", "p", "p", "p", "p", "p", "p", "p" },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ "P", "P", "P", "P", "P", "P", "P", "P" },
					{ "R", "N", "B", "Q", "K", "B", "N", "R" },
				},
				["en_passant"] = "-",
				["castling"] = "KQkq",
				["player"] = "w",
				["halfmove"] = "0",
			} },
			{ cmd = "rnbqkbnr/ppp1pppp/8/3p4/8/8/PPPPPPPP/RNBQKBNR w KQkq d6 0 2", passed = true, expected = {
				["fullmove"] = "2",
				["board"] = {
					{ "r", "n", "b", "q", "k", "b", "n", "r" },
					{ "p", "p", "p", " ", "p", "p", "p", "p" },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", "p", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ "P", "P", "P", "P", "P", "P", "P", "P" },
					{ "R", "N", "B", "Q", "K", "B", "N", "R" },
				},
				["en_passant"] = "d6",
				["castling"] = "KQkq",
				["player"] = "w",
				["halfmove"] = "0",
			} },

			{ cmd = "rnbqkb1r/pppppppp/5n2/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 1 2", passed = true, expected = {
				["fullmove"] = "2",
				["board"] = {
					{ "r", "n", "b", "q", "k", "b", " ", "r" },
					{ "p", "p", "p", "p", "p", "p", "p", "p" },
					{ " ", " ", " ", " ", " ", "n", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ "P", "P", "P", "P", "P", "P", "P", "P" },
					{ "R", "N", "B", "Q", "K", "B", "N", "R" },
				},
				["en_passant"] = "-",
				["castling"] = "KQkq",
				["player"] = "w",
				["halfmove"] = "1",
			} },

			{ cmd = "rnbqkbnr/pppp1ppp/8/4p3/8/8/PPPPPPPP/RNBQKBNR w KQkq e6 0 2", passed = true, expected = {
				["fullmove"] = "2",
				["board"] = {
					{ "r", "n", "b", "q", "k", "b", "n", "r" },
					{ "p", "p", "p", "p", " ", "p", "p", "p" },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", "p", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ "P", "P", "P", "P", "P", "P", "P", "P" },
					{ "R", "N", "B", "Q", "K", "B", "N", "R" },
				},
				["en_passant"] = "e6",
				["castling"] = "KQkq",
				["player"] = "w",
				["halfmove"] = "0",
			} },

			{ cmd = "r3k2r/ppp2ppp/2n5/3pp3/8/2N5/PPPP1PPP/R3K2R w KQkq - 0 10", passed = true, expected = {
				["fullmove"] = "10",
				["board"] = {
					{ "r", " ", " ", " ", "k", " ", " ", "r" },
					{ "p", "p", "p", " ", " ", "p", "p", "p" },
					{ " ", " ", "n", " ", " ", " ", " ", " " },
					{ " ", " ", " ", "p", "p", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", "N", " ", " ", " ", " ", " " },
					{ "P", "P", "P", "P", " ", "P", "P", "P" },
					{ "R", " ", " ", " ", "K", " ", " ", "R" },
				},
				["en_passant"] = "-",
				["castling"] = "KQkq",
				["player"] = "w",
				["halfmove"] = "0",
			} },

			{ cmd = "rnbq1bnr/ppppkppp/8/4p3/8/8/PPPPPPPP/RNBQKBNR w KQ - 1 5", passed = true, expected = {
				["fullmove"] = "5",
				["board"] = {
					{ "r", "n", "b", "q", " ", "b", "n", "r" },
					{ "p", "p", "p", "p", "k", "p", "p", "p" },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", "p", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ " ", " ", " ", " ", " ", " ", " ", " " },
					{ "P", "P", "P", "P", "P", "P", "P", "P" },
					{ "R", "N", "B", "Q", "K", "B", "N", "R" },
				},
				["en_passant"] = "-",
				["castling"] = "KQ",
				["player"] = "w",
				["halfmove"] = "1",
			} },
		}

	for i, case in ipairs(test_cases) do
		local ok, output = pcall(Utils.fen_to_table, case.cmd)
		if not ok then
			failed = failed + 1
			Base.error("Fen to table failed with an error at [" .. i .. "]: " .. case.cmd .. " Error: " .. output, -1)
			goto skip
		end
		if not (compare_fen_tables(output, case.expected)) then
			failed = failed + 1
			Base.error(
				"Fen to table failed at test ["
					.. i
					.. "]: "
					.. case.cmd
					.. " Expected "
					.. Json.encode(case.expected)
					.. " but got "
					.. Json.encode(output),
				-1
			)
		end
		::skip::
	end
	print("\nTotal failed tests: " .. failed .. "/" .. #test_cases)
	return failed
end

test.all = function()
	local c, t
	c = test.json_test_legal()
	c = c + test.json_test_illegal()
	print_header("JSON", c)
	c = test.utils_test_debug()
	print_header("Error Messages", c)
	c = test.fen_to_table_test()
	print_header("Fen", c)
end

return test
