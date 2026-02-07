// Theme Switcher Module
// Handles toggling between light and dark modes

(function () {
  // Theme constants
  const THEME_KEY = "theme";
  const DARK_THEME = "dark";
  const LIGHT_THEME = "light";

  // Get current theme from localStorage
  function getCurrentTheme() {
    return localStorage.getItem(THEME_KEY) || DARK_THEME;
  }

  // Toggle theme and reload page
  function toggleTheme() {
    const currentTheme = getCurrentTheme();
    const newTheme = currentTheme === DARK_THEME ? LIGHT_THEME : DARK_THEME;

    // Save to localStorage
    localStorage.setItem(THEME_KEY, newTheme);

    // Reload page to apply new theme (CSS loaded at page start based on localStorage)
    window.location.reload();
  }

  // Update button text based on current theme
  function updateButtonText(button) {
    if (!button) return;

    const currentTheme = getCurrentTheme();

    if (currentTheme === DARK_THEME) {
      // Currently dark, offer to switch to light
      button.textContent = "Light Mode";
      button.setAttribute("aria-label", "Switch to light mode");
    } else {
      // Currently light, offer to switch to dark
      button.textContent = "Dark Mode";
      button.setAttribute("aria-label", "Switch to dark mode");
    }
  }

  // Initialize theme switcher
  function init() {
    // Find theme toggle button
    const themeToggle = document.getElementById("theme-toggle-btn");

    if (themeToggle) {
      // Set initial text
      updateButtonText(themeToggle);

      // Add click handler
      themeToggle.addEventListener("click", (e) => {
        e.preventDefault();
        toggleTheme();
      });
    }
  }

  // Run when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Expose API for other scripts if needed
  window.ThemeSwitcher = {
    toggle: toggleTheme,
    getCurrent: getCurrentTheme,
    updateButton: updateButtonText,
  };
})();
