// Shared top-nav behaviour — include on every authenticated page.
// Each nav button is wired only if (a) it exists in the DOM and
// (b) we are not already on that page.

document.addEventListener("DOMContentLoaded", () => {
  const path = window.location.pathname;

  // ── Home ─────────────────────────────────────────────────────────────────
  const homeBtn = document.getElementById("home-btn");
  if (homeBtn) {
    homeBtn.addEventListener("click", () => {
      window.location.href = "/home";
    });
  }

  // ── My Stats ─────────────────────────────────────────────────────────────
  const statsBtn = document.getElementById("stats-btn");
  if (statsBtn) {
    statsBtn.addEventListener("click", () => {
      window.location.href = "/stats";
    });
  }

  // ── Profile ──────────────────────────────────────────────────────────────
  const profileBtn = document.getElementById("profile-btn");
  if (profileBtn) {
    profileBtn.addEventListener("click", () => {
      window.location.href = "/profile";
    });
  }

  // ── Logout ───────────────────────────────────────────────────────────────
  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        const response = await fetch("/logout", {
          method: "POST",
          credentials: "include",
        });

        const data = await response.json();

        if (data.success) {
          window.location.href = "/login";
        }
      } catch (error) {
        console.error("Logout error:", error);
      }
    });
  }
});
