requireGuest();

const form = document.getElementById("login-form");
const feedback = document.getElementById("feedback");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  feedback.textContent = "";
  feedback.className = "error";

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  if (!email || !password) {
    feedback.textContent = "Informe e-mail e senha.";
    return;
  }

  try {
    await signIn(email, password);
    location.href = "module-select.html";
  } catch (err) {
    feedback.textContent = err.message || "Falha no login.";
  }
});
