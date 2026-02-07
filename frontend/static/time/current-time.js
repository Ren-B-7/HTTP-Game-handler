function updateTime() {
  const el = document.getElementById("current-time");
  if (!el) return;

  el.textContent = new Date().toLocaleTimeString();
}

updateTime(); // run once
setInterval(updateTime, 1000);
