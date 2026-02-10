// ─── Utility functions ───────────────────────────────────────────────────────
function showMessage(elementId, message, isSuccess = false) {
  const el = document.getElementById(elementId);
  el.textContent = message;
  el.style.display = "block";
  if (isSuccess) {
    el.classList.add("success");
  } else {
    el.classList.remove("success");
  }
}

function clearMessages(prefix) {
  document.getElementById(`${prefix}-error`).style.display = "none";
  document.getElementById(`${prefix}-success`).style.display = "none";
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
        img.src = "icons/eye_open.svg";
      } else {
        input.type = "password";
        img.src = "icons/eye_slash.svg";
      }
    });
  });
}

// ─── Load current user info ──────────────────────────────────────────────────
async function loadUserInfo() {
  try {
    const response = await fetch("/session", {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) {
      if (response.status === 401) {
        window.location.href = "/login";
        throw new Error("unauthorized");
      }
      throw new Error("Failed to fetch stats");
    }

    const data = await response.json();
    document.getElementById("current-username").textContent =
      data.username || "—";
  } catch (error) {
    console.error("Error loading user info:", error);
  }
}

// ─── Handle username change ──────────────────────────────────────────────────
async function handleUsernameChange(e) {
  e.preventDefault();
  clearMessages("username");

  const newUsername = document.getElementById("new-username").value.trim();
  const password = document.getElementById("confirm-password-username").value;
  const submitBtn = e.target.querySelector('button[type="submit"]');

  if (!newUsername) {
    showMessage("username-error", "Please enter a new username");
    return;
  }

  if (newUsername.length < 3 || newUsername.length > 20) {
    showMessage("username-error", "Username must be 3-20 characters");
    return;
  }

  if (!password) {
    showMessage("username-error", "Please enter your password to confirm");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Updating...";

  try {
    const response = await fetch("/profile/update-username", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ new_username: newUsername, password }),
    });

    const data = await response.json();

    if (data.success) {
      showMessage("username-success", "Username updated successfully!", true);
      document.getElementById("current-username").textContent = newUsername;
      document.getElementById("new-username").value = "";
      document.getElementById("confirm-password-username").value = "";
    } else {
      showMessage(
        "username-error",
        data.message || "Failed to update username",
      );
    }
  } catch (error) {
    console.error("Username update error:", error);
    showMessage("username-error", "Connection error. Please try again.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Update Username";
  }
}

// ─── Handle password change ──────────────────────────────────────────────────
async function handlePasswordChange(e) {
  e.preventDefault();
  clearMessages("password");

  const currentPassword = document.getElementById("current-password").value;
  const newPassword = document.getElementById("new-password").value;
  const confirmPassword = document.getElementById("confirm-new-password").value;
  const submitBtn = e.target.querySelector('button[type="submit"]');

  if (!currentPassword || !newPassword || !confirmPassword) {
    showMessage("password-error", "Please fill in all fields");
    return;
  }

  if (newPassword.length < 12) {
    showMessage("password-error", "Password must be at least 12 characters");
    return;
  }

  if (newPassword !== confirmPassword) {
    showMessage("password-error", "New passwords do not match");
    return;
  }

  if (newPassword === currentPassword) {
    showMessage(
      "password-error",
      "New password must be different from current password",
    );
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Updating...";

  try {
    const response = await fetch("/profile/update-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    });

    const data = await response.json();

    if (data.success) {
      showMessage("password-success", "Password updated successfully!", true);
      document.getElementById("current-password").value = "";
      document.getElementById("new-password").value = "";
      document.getElementById("confirm-new-password").value = "";
      document.getElementById("password-strength").style.display = "none";
    } else {
      showMessage(
        "password-error",
        data.message || "Failed to update password",
      );
    }
  } catch (error) {
    console.error("Password update error:", error);
    showMessage("password-error", "Connection error. Please try again.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Update Password";
  }
}

// ─── Handle account deletion ─────────────────────────────────────────────────
function showDeleteModal() {
  document.getElementById("delete-modal").style.display = "flex";
}

function hideDeleteModal() {
  document.getElementById("delete-modal").style.display = "none";
  document.getElementById("delete-password").value = "";
  document.getElementById("delete-error").style.display = "none";
}

async function handleAccountDeletion() {
  const password = document.getElementById("delete-password").value;
  const confirmBtn = document.getElementById("confirm-delete-btn");

  if (!password) {
    showMessage("delete-error", "Please enter your password");
    return;
  }

  confirmBtn.disabled = true;
  confirmBtn.textContent = "Deleting...";

  try {
    const response = await fetch("/profile/delete-account", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ password }),
    });

    const data = await response.json();

    if (data.success) {
      // Account deleted, redirect to login
      window.location.href = "/login";
    } else {
      showMessage("delete-error", data.message || "Failed to delete account");
      confirmBtn.disabled = false;
      confirmBtn.textContent = "Delete My Account";
    }
  } catch (error) {
    console.error("Account deletion error:", error);
    showMessage("delete-error", "Connection error. Please try again.");
    confirmBtn.disabled = false;
    confirmBtn.textContent = "Delete My Account";
  }
}

// ─── Initialize ──────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  loadUserInfo();
  setupPasswordToggles();

  // Username form
  document
    .getElementById("username-form")
    .addEventListener("submit", handleUsernameChange);

  // Password form
  document
    .getElementById("password-form")
    .addEventListener("submit", handlePasswordChange);

  // Password strength checker
  document.getElementById("new-password").addEventListener("input", (e) => {
    checkPasswordStrength(e.target.value);
  });

  // Delete account
  document
    .getElementById("delete-account-btn")
    .addEventListener("click", showDeleteModal);
  document
    .getElementById("cancel-delete-btn")
    .addEventListener("click", hideDeleteModal);
  document
    .getElementById("confirm-delete-btn")
    .addEventListener("click", handleAccountDeletion);

  // Close modal on outside click
  document.getElementById("delete-modal").addEventListener("click", (e) => {
    if (e.target.id === "delete-modal") {
      hideDeleteModal();
    }
  });
});
