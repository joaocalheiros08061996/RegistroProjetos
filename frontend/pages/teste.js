document.getElementById("save-token-btn").addEventListener("click", () => {
  setToken("TOKEN_TESTE");
  alert("Token salvo");
});

document.getElementById("read-token-btn").addEventListener("click", () => {
  alert(`Token atual: ${getToken()}`);
});

document.getElementById("logout-btn").addEventListener("click", logout);
