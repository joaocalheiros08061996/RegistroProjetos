requireGuest();

const form = document.getElementById("register-form");
const feedback = document.getElementById("feedback");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  feedback.textContent = "";
  feedback.className = "status";

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const privacyNoticeAcknowledged = document.getElementById(
    "privacy-notice-acknowledged"
  ).checked;

  if (!email || !password || !privacyNoticeAcknowledged) {
    feedback.textContent = "Informe e-mail, senha e confirme a ciência do Aviso de Privacidade.";
    feedback.className = "error";
    return;
  }

  try {
    await signUp(email, password, privacyNoticeAcknowledged);

    if (getToken()) {
      feedback.textContent = "Conta criada e autenticada. Redirecionando...";
      feedback.className = "success";
      setTimeout(() => {
        location.href = "module-select.html";
      }, 500);
      return;
    }

    feedback.textContent = "Conta criada com sucesso. Agora faça login.";
    feedback.className = "success";
    setTimeout(() => {
      location.href = "login.html";
    }, 900);
  } catch (err) {
    feedback.textContent = err.message || "Falha no cadastro.";
    feedback.className = "error";
  }
});
