// ─── Utility functions ───────────────────────────────────────────────────────
function showError(msg) {
  const el = document.getElementById("error-message");
  el.textContent = msg;
  el.style.display = "block";
  document.getElementById("success-message").style.display = "none";
}

function showSuccess(msg) {
  const el = document.getElementById("success-message");
  el.textContent = msg;
  el.style.display = "block";
  document.getElementById("error-message").style.display = "none";
}

function clearMessages() {
  document.getElementById("error-message").style.display = "none";
  document.getElementById("success-message").style.display = "none";
}

function checkPasswordStrength(password) {
  const strength = document.getElementById("password-strength");
  if (!password) {
    strength.style.display = "none";
    return;
  }

  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^a-zA-Z\d]/.test(password)) score++;

  strength.style.display = "block";
  strength.className = "password-strength";

  if (score <= 2) {
    strength.textContent = "Weak";
    strength.classList.add("strength-weak");
  } else if (score <= 4) {
    strength.textContent = "Medium";
    strength.classList.add("strength-medium");
  } else {
    strength.textContent = "Strong";
    strength.classList.add("strength-strong");
  }
}

// ─── Form submission ─────────────────────────────────────────────────────────
async function handleRegister(e) {
  e.preventDefault();
  clearMessages();

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  const confirmPassword = document.getElementById("confirm_password").value;
  const submitButton = e.target.querySelector('button[type="submit"]');

  // Validation
  if (!username || !password || !confirmPassword) {
    showError("Please fill in all fields");
    return;
  }

  if (username.length < 3 || username.length > 20) {
    showError("Username must be 3-20 characters");
    return;
  }

  if (password.length < 8) {
    showError("Password must be at least 8 characters");
    return;
  }

  if (password !== confirmPassword) {
    showError("Passwords do not match");
    return;
  }

  // Disable button during submission
  submitButton.disabled = true;
  submitButton.textContent = "Registering...";

  try {
    const response = await fetch("/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}&confirm_password=${encodeURIComponent(confirmPassword)}`,
    });

    const data = await response.json();

    if (data.success) {
      showSuccess("Registration successful! Redirecting...");
      setTimeout(() => {
        window.location.href = data.redirect || "/login";
      }, 1000);
    } else {
      showError(data.message || "Registration failed");
      submitButton.disabled = false;
      submitButton.textContent = "Register";
    }
  } catch (error) {
    console.error("Registration error:", error);
    showError("Connection error. Please try again.");
    submitButton.disabled = false;
    submitButton.textContent = "Register";
  }
}

// ─── Initialize ──────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Form submission
  document
    .getElementById("registerForm")
    .addEventListener("submit", handleRegister);

  // Password strength checker
  const passwordField = document.getElementById("password");
  passwordField.addEventListener("input", (e) => {
    checkPasswordStrength(e.target.value);
  });

  // Enter key support on confirm password
  document
    .getElementById("confirm_password")
    .addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        document
          .getElementById("registerForm")
          .dispatchEvent(new Event("submit"));
      }
    });
});
