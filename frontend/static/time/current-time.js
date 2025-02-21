async function updateTime() {
  const now = new Date();
  document.getElementById("current-time").textContent =
    now.toLocaleTimeString();
}
setInterval(updateTime, 1000); // Update time every second
window.onload = updateTime;
