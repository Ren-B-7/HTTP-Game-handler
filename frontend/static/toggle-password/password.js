(function () {
  function setupPasswordToggles() {
    document
      .querySelectorAll(".password-container[data-password-toggle]")
      .forEach((container) => {
        const input = container.querySelector(
          "input[type='password'], input[type='text']",
        );
        const button = container.querySelector(".eye-icon");
        const img = button?.querySelector(".img");

        // Hard stop if structure isn't exactly right
        if (!input || !button || !img) return;

        button.addEventListener("click", (e) => {
          e.preventDefault();

          const isHidden = input.type === "password";
          input.type = isHidden ? "text" : "password";

          img.src = isHidden ? "/icons/eye_open.svg" : "/icons/eye_slash.svg";

          img.alt = isHidden ? "Hide password" : "Show password";
        });
      });
  }

  // DOM safe, works with defer
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupPasswordToggles);
  } else {
    setupPasswordToggles();
  }
})();
