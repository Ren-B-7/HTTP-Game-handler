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

// ─── Password visibility toggle ──────────────────────────────────────────────
function setupPasswordToggles() {
  document.querySelectorAll(".eye-icon").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const container = btn.closest(".password-container");
      const input = container.querySelector("input");
      const img = btn.querySelector(".eye-img");

      if (input.type === "password") {
        input.type = "text";
        img.src = "/icons/eye_open.svg";
      } else {
        input.type = "password";
        img.src = "/icons/eye_slash.svg";
      }
    });
  });
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

  if (password.length < 12) {
    showError("Password must be at least 12 characters");
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
  // Setup password toggles
  setupPasswordToggles();

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
