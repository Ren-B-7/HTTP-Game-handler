function checkPasswordStrength(password) {
  const strength = document.getElementById("password-strength");
  if (!password) {
    strength.style.display = "none";
    return;
  }

  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^a-zA-Z\d]/.test(password)) score++;

  strength.style.display = "block";
  strength.className = "password-strength";

  if (score <= 2) {
    strength.textContent = "Weak";
    strength.classList.add("strength-weak");
  } else if (score <= 4) {
    strength.textContent = "Medium";
    strength.classList.add("strength-medium");
  } else {
    strength.textContent = "Strong";
    strength.classList.add("strength-strong");
  }
}
