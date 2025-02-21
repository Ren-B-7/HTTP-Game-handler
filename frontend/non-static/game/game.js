// Theme toggle logic
const lightTheme = document.getElementById("light-theme");
const lightBoard = document.getElementById("board-l-theme");

const darkTheme = document.getElementById("dark-theme");
const darkBoard = document.getElementById("board-d-theme");

const toggleButton = document.getElementById("toggle-theme");

/**
 * Gets the value of a cookie by name.
 *
 * @param {string} name - The name of the cookie to retrieve.
 * @returns {string|null} The value of the cookie if found, null otherwise.
 * @author Renier Barnard
 */
function getCookie(name) {
  let cookies = document.cookie.split("; ");
  for (let cookie of cookies) {
    let [key, value] = cookie.split("="); // Split key-value pair
    if (key === name) {
      return value; // Return the value if name matches
    }
  }
  return null; // Return null if cookie not found
}

/**
 * Sets a cookie with the given name, value, and optional number of days to
 * expire.
 *
 * @param {string} name - The name of the cookie.
 * @param {string} value - The value of the cookie.
 * @param {number} [days] - The number of days until the cookie expires.
 * If not provided, the cookie is a session cookie.
 * @author Renier Barnard
 */
function setCookie(name, value, days) {
  let expires = "";
  if (days) {
    let date = new Date();
    date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
    expires = "; expires=" + date.toUTCString();
  }
  document.cookie =
    name + "=" + value + "; path=/" + expires + "; samesite=lax";
}
function toggleTheme() {
  let theme = getCookie("theme") === "1" ? "0" : "1";
  setCookie("theme", theme, 365); // Store for 1 year
  applytheme();
}
/**
 * Applies the theme stored in the cookie to the page.
 * @author Renier Barnard
 */
function applytheme() {
  let theme = getCookie("theme");
  if (theme == 1) {
    lightTheme.disabled = true;
    lightBoard.disabled = true;
    darkTheme.disabled = false;
    darkBoard.disabled = false;
  } else {
    lightTheme.disabled = false;
    lightBoard.disabled = false;
    darkTheme.disabled = true;
    darkBoard.disabled = true;
  }
}

/**
 * Returns the image URL for a chess piece based on its theme.
 *
 * For white pieces, it uses the Wikipedia theme, and for black pieces,
 * it uses the Alpha theme. The function determines the theme by checking
 * if the piece string contains 'w' for white pieces.
 *
 * @param {string} piece - The identifier for the chess piece, e.g., 'wp' for white pawn.
 * @returns {string} The URL to the image of the specified chess piece.
 * @author Renier Barnard
 */

function pieceTheme(piece) {
  // wikipedia theme for white pieces
  const img_location = "/static/game/game_depends/img/chesspieces/";
  if (piece.search(/w/) !== -1) {
    return img_location + piece + ".png";
  }

  // alpha theme for black pieces
  return img_location + piece + ".png";
}

var config = {
  pieceTheme: pieceTheme,
  position: "start",
  draggable: true,
};
document.addEventListener("DOMContentLoaded", function () {
  applytheme();
  var board = Chessboard("board1", config);

  board.position("start"); // Start with the initial chess position
  // Attach toggle function to button
  document
    .getElementById("theme-toggle")
    .addEventListener("click", toggleTheme);
});
