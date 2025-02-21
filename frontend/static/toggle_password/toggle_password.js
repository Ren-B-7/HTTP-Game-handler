// Toggle password visibility
async function togglePassword(id) {
  var passwordField = document.getElementById(id);
  passwordField.type = passwordField.type === "password" ? "text" : "password";
}
