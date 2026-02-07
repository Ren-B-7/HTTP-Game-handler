// ─── API helpers ─────────────────────────────────────────────────────────────
async function fetchStats() {
  const response = await fetch("/stats", {
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

  return response.json();
}

// ─── Display helpers ─────────────────────────────────────────────────────────
function formatDate(dateString) {
  if (!dateString) return "—";

  const date = new Date(dateString);
  const now = new Date();
  const diffTime = Math.abs(now - date);
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return `${weeks} week${weeks > 1 ? "s" : ""} ago`;
  }
  if (diffDays < 365) {
    const months = Math.floor(diffDays / 30);
    return `${months} month${months > 1 ? "s" : ""} ago`;
  }
  const years = Math.floor(diffDays / 365);
  return `${years} year${years > 1 ? "s" : ""} ago`;
}

function displayStats(data) {
  document.getElementById("player-name").textContent = data.username || "—";
  document.getElementById("elo").textContent = data.elo ?? "—";
  document.getElementById("wins").textContent = data.wins ?? "—";
  document.getElementById("draws").textContent = data.draws ?? "—";
  document.getElementById("losses").textContent = data.losses ?? "—";
  document.getElementById("games-played").textContent =
    data.wins + data.draws + data.losses ?? "—";
  document.getElementById("last-played").textContent = data.last_game
    ? formatDate(data.last_played)
    : "Never";
  document.getElementById("date-joined").textContent = data.date_joined
    ? formatDate(data.date_joined)
    : "—";
}

// ─── Main logic ──────────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const data = await fetchStats();
    displayStats(data);
  } catch (error) {
    console.error("Error loading stats:", error);
  }
}

// ─── Event handlers ──────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  loadStats();

  // Support Enter key to reload stats
  document.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      loadStats();
    }
  });
});
