const API_BASE = "";
const TOKEN_KEY = "access_token";

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
    location.href = "projects.html";
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
    throw new Error("Nao foi possivel carregar a configuracao da aplicacao.");
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
    throw new Error("Sessao expirada. Faca login novamente.");
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

async function supabaseAuth(path, payload) {
  const cfg = await getAppConfig();
  if (!cfg.supabase_url || !cfg.supabase_anon_key) {
    throw new Error("Supabase nao configurado no backend.");
  }

  const res = await fetch(`${cfg.supabase_url}/auth/v1/${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: cfg.supabase_anon_key,
    },
    body: JSON.stringify(payload),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error_description || data.msg || "Falha na autenticacao.");
  }

  return data;
}

async function signIn(email, password) {
  const data = await supabaseAuth("token?grant_type=password", { email, password });

  if (!data.access_token) {
    throw new Error("Token de acesso nao retornado pelo Supabase.");
  }

  setToken(data.access_token);
  return data;
}

async function signUp(email, password) {
  return supabaseAuth("signup", { email, password });
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
window.signIn = signIn;
window.signUp = signUp;
window.qs = qs;
