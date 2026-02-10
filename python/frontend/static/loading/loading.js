// Show loading screen when navigating away
window.addEventListener("beforeunload", function () {
  document.getElementById("loading").style.display = "flex";
});

// Hide loading screen once the page fully loads
window.addEventListener("load", function () {
  document.getElementById("loading").style.display = "none";
});

// Hide loading screen when restored from back/forward cache
// (back/forward navigation often skips "load", but pageshow always fires)
window.addEventListener("pageshow", function (e) {
  if (event.persisted) {
    document.getElementById("loading").style.display = "none";
  }
});
