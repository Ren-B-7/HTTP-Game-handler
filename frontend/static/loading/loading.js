// Show loading screen when navigating
window.addEventListener("beforeunload", function async() {
  document.getElementById("loading").style.display = "flex";
});

// Hide loading screen once the page loads
window.addEventListener("load", function async() {
  document.getElementById("loading").style.display = "none";
});
