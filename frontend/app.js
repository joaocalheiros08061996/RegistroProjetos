const API_BASE = "";
const TOKEN_KEY = "access_token";
const AUTHENTICATED_HOME = "module-select.html";

let appConfigCache = null;

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function isAuthenticated() {
  return Boolean(getToken());
}

function logout() {
  clearToken();
  location.href = "login.html";
}

function requireAuth() {
  if (!isAuthenticated()) {
    location.href = "login.html";
    return false;
  }
  return true;
}

function requireGuest() {
  if (isAuthenticated()) {
    location.href = AUTHENTICATED_HOME;
    return false;
  }
  return true;
}

async function getAppConfig() {
  if (appConfigCache) {
    return appConfigCache;
  }

  const res = await fetch("/app/config");
  if (!res.ok) {
    throw new Error("Não foi possível carregar a configuração da aplicação.");
  }

  appConfigCache = await res.json();
  return appConfigCache;
}

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    ...(options.headers || {}),
  };

  if (!headers["Content-Type"] && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(API_BASE + path, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    logout();
    throw new Error("Sessão expirada. Faça login novamente.");
  }

  if (res.status === 204) {
    return null;
  }

  const contentType = res.headers.get("content-type") || "";
  const hasJson = contentType.includes("application/json");
  const payload = hasJson ? await res.json() : await res.text();

  if (!res.ok) {
    if (payload && typeof payload === "object" && payload.detail) {
      throw new Error(payload.detail);
    }
    throw new Error(typeof payload === "string" ? payload : `Erro HTTP ${res.status}`);
  }

  return payload;
}

function normalizeIsoFromInput(value) {
  if (!value) {
    return null;
  }
  return new Date(value).toISOString();
}

function toLocalInputValue(date) {
  const d = date || new Date();
  const tzOffset = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - tzOffset).toISOString().slice(0, 16);
}

function formatDateTime(isoValue) {
  if (!isoValue) {
    return "-";
  }

  const date = new Date(isoValue);
  if (Number.isNaN(date.getTime())) {
    return String(isoValue);
  }

  return date.toLocaleString("pt-BR");
}

function formatSeconds(totalSeconds) {
  const seconds = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  const hh = String(Math.floor(seconds / 3600)).padStart(2, "0");
  const mm = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  return `${hh}:${mm}:${ss}`;
}

function formatProjectType(projectType) {
  const labels = {
    LAYOUT: "LAYOUT",
    EXPORTACAO: "EXPORTAÇÃO",
    NORMATIZACAO: "NORMATIZAÇÃO",
    PADRONIZACAO: "PADRONIZAÇÃO",
    TRY_OUT: "TRY OUT",
    MAPEAMENTO: "MAPEAMENTO",
    MELHORIA: "MELHORIA DE PROC. EXISTENTES",
    MELHORIA_PROC_NOVOS: "MELHORIA DE PROC. NOVOS",
    PECAS: "PEÇAS",
  };

  if (labels[projectType]) {
    return labels[projectType];
  }

  return String(projectType || "")
    .replaceAll("_", " ")
    .toUpperCase();
}

async function supabaseAuth(path, payload) {
  const action = path.startsWith("token") ? "login" : "signup";
  const res = await fetch(`/auth/${action}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(
      data.detail ||
      data.error_description ||
      data.msg ||
      "Falha na autenticação."
    );
  }

  return data;
}

async function signIn(email, password) {
  const data = await supabaseAuth("token?grant_type=password", { email, password });

  if (!data.access_token) {
    throw new Error("Token de acesso não retornado pelo Supabase.");
  }

  setToken(data.access_token);
  return data;
}

async function signUp(email, password) {
  const data = await supabaseAuth("signup", { email, password });

  // Em projetos Supabase sem confirmação obrigatória de e-mail,
  // o signup pode devolver token imediatamente.
  const tokenFromResponse =
    data?.access_token ||
    data?.session?.access_token ||
    null;

  if (tokenFromResponse) {
    setToken(tokenFromResponse);
  }

  return data;
}

function qs(name) {
  return new URLSearchParams(location.search).get(name);
}

window.getToken = getToken;
window.setToken = setToken;
window.clearToken = clearToken;
window.logout = logout;
window.requireAuth = requireAuth;
window.requireGuest = requireGuest;
window.getAppConfig = getAppConfig;
window.apiFetch = apiFetch;
window.normalizeIsoFromInput = normalizeIsoFromInput;
window.toLocalInputValue = toLocalInputValue;
window.formatDateTime = formatDateTime;
window.formatSeconds = formatSeconds;
window.formatProjectType = formatProjectType;
window.signIn = signIn;
window.signUp = signUp;
window.qs = qs;
