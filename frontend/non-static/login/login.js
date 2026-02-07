// Login form handler
const password_btn = document.getElementById("password");
const registerBtn = document.getElementById("register-button");
// Handle Enter key on password field
password_btn.addEventListener("keypress", function (e) {
  if (e.key === "Enter") {
    document.getElementById("loginForm").dispatchEvent(new Event("submit"));
  }
});

// Register navigation
if (registerBtn) {
  registerBtn.addEventListener("click", () => {
    window.location.href = "/register";
  });
}
document
  .getElementById("loginForm")
  .addEventListener("submit", async function (e) {
    e.preventDefault();

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    const errorDiv = document.getElementById("error-message");
    const successDiv = document.getElementById("success-message");
    const submitButton = this.querySelector('button[type="submit"]');

    // Clear previous messages
    errorDiv.style.display = "none";
    successDiv.style.display = "none";

    // Validation
    if (!username || !password) {
      errorDiv.textContent = "Please enter both username and password";
      errorDiv.style.display = "block";
      return;
    }

    // Disable button during submission
    submitButton.disabled = true;
    submitButton.textContent = "Logging in...";

    try {
      const response = await fetch("/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
      });

      const data = await response.json();

      if (data.success) {
        successDiv.textContent = "Login successful! Redirecting...";
        successDiv.style.display = "block";

        // Redirect to home page
        setTimeout(() => {
          window.location.href = data.redirect || "/home";
        }, 500);
      } else {
        errorDiv.textContent = data.message || "Invalid username or password";
        errorDiv.style.display = "block";
        submitButton.disabled = false;
        submitButton.textContent = "Login";
      }
    } catch (error) {
      console.error("Login error:", error);
      errorDiv.textContent = "Connection error. Please try again.";
      errorDiv.style.display = "block";
      submitButton.disabled = false;
      submitButton.textContent = "Login";
    }
  });
