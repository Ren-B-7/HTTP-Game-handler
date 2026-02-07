// ─── helpers (same show/hide pattern used by login.js / register.js) ────────
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

function setStatus(msg, searching = false) {
  const el = document.getElementById("status-text");
  el.textContent = msg;
  el.classList.toggle("searching", searching);
}

// ─── main ────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const findBtn = document.getElementById("find-game-btn");
  const cancelBtn = document.getElementById("cancel-search-btn");

  // ── 1. session check — pull username + elo, redirect if not authed ──────
  fetch("/session", {
    method: "POST",
    credentials: "include",
  })
    .then((response) => {
      if (!response.ok) {
        window.location.href = "/login";
        throw new Error("unauthorized");
      }
      return response.json();
    })
    .then((data) => {
      document.getElementById("username").textContent =
        data.username || "Player";
      document.getElementById("elo").textContent = data.elo ?? "—";
    })
    .catch(() => {}); // redirect already fired on !ok

  // ── 2. find game ─────────────────────────────────────────────────────────
  findBtn.addEventListener("click", async () => {
    clearMessages();
    findBtn.disabled = true;
    findBtn.textContent = "Searching…";

    try {
      const response = await fetch("/home/search", {
        method: "POST",
        credentials: "include",
      });

      const data = await response.json();

      if (data.success) {
        // swap buttons: hide Find, show Cancel
        findBtn.style.display = "none";
        cancelBtn.style.display = "inline-block";
        setStatus("Searching for an opponent…", true);
      } else {
        showError(data.message || "Could not start search.");
        findBtn.disabled = false;
        findBtn.textContent = "Find Game";
      }
    } catch (error) {
      console.error("Search error:", error);
      showError("Connection error. Please try again.");
      findBtn.disabled = false;
      findBtn.textContent = "Find Game";
    }
  });

  // ── 4. cancel search ─────────────────────────────────────────────────────
  cancelBtn.addEventListener("click", async () => {
    clearMessages();
    cancelBtn.disabled = true;
    cancelBtn.textContent = "Cancelling…";

    try {
      const response = await fetch("/home/cancel", {
        method: "POST",
        credentials: "include",
      });

      const data = await response.json();

      if (data.success) {
        // swap back: show Find, hide Cancel
        cancelBtn.style.display = "none";
        findBtn.style.display = "inline-block";
        findBtn.disabled = false;
        findBtn.textContent = "Find Game";
        setStatus("");
      } else {
        showError(data.message || "Could not cancel search.");
        cancelBtn.disabled = false;
        cancelBtn.textContent = "Cancel";
      }
    } catch (error) {
      console.error("Cancel error:", error);
      showError("Connection error. Please try again.");
      cancelBtn.disabled = false;
      cancelBtn.textContent = "Cancel";
    }
  });
});
