// Shared front-end helpers for calling the JSON API with JWT.

function getToken() {
  return localStorage.getItem("token");
}

function setToken(token) {
  if (token) localStorage.setItem("token", token);
  else localStorage.removeItem("token");
  renderAuthInfo();
}

function clearToken() {
  localStorage.removeItem("token");
  renderAuthInfo();
}

function base64UrlDecode(input) {
  // Convert base64url -> base64 then decode.
  const base64 = input.replace(/-/g, "+").replace(/_/g, "/");
  const pad = base64.length % 4 ? "=".repeat(4 - (base64.length % 4)) : "";
  const str = atob(base64 + pad);
  // Handle UTF-8.
  try {
    return decodeURIComponent(
      Array.prototype.map
        .call(str, (c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
  } catch {
    return str;
  }
}

function getJwtPayload() {
  const token = getToken();
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    return JSON.parse(base64UrlDecode(parts[1]));
  } catch {
    return null;
  }
}

function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function api(path, options = {}) {
  const url = path.startsWith("/api") ? path : "/api" + path;
  const token = getToken();
  const isLogin = url === "/api/auth/login";

  // Allow login without an existing JWT.
  if (!token && !isLogin) {
    throw { error: "Authentication required. Please login on Home." };
  }

  const method = options.method ? options.method.toUpperCase() : "GET";
  const headers = Object.assign(
    {},
    options.headers || {}
  );
  if (token) {
    headers.Authorization = "Bearer " + token;
  }

  let body = undefined;
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const res = await fetch(url, { method, headers, body });
  const contentType = res.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await res.json() : await res.text();

  if (!res.ok) {
    const err = data && data.error ? data.error : res.statusText;
    throw { error: err };
  }

  return data;
}

function renderAuthInfo() {
  const el = document.getElementById("auth-info");
  if (!el) return;

  const payload = getJwtPayload();
  if (!payload) {
    el.textContent = "Not logged in";
    const boothsLink = document.getElementById("nav-booths");
    const usersLink = document.getElementById("nav-users");
    if (boothsLink) boothsLink.style.display = "none";
    if (usersLink) usersLink.style.display = "none";
    return;
  }

  const role = payload.role ? String(payload.role) : "user";
  const rid = payload.restaurant_id ? String(payload.restaurant_id) : "";
  el.textContent = rid ? `Logged in (${role}, restaurant ${rid})` : `Logged in (${role})`;

  const isAdmin = role === "admin";
  const boothsLink = document.getElementById("nav-booths");
  const usersLink = document.getElementById("nav-users");
  if (boothsLink) boothsLink.style.display = isAdmin ? "inline-block" : "none";
  if (usersLink) usersLink.style.display = isAdmin ? "inline-block" : "none";
}

window.getJwtPayload = getJwtPayload;
window.escapeHtml = escapeHtml;
window.api = api;
window.setToken = setToken;
window.logout = async function logout() {
  const token = getToken();
  if (token) {
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: {
          Authorization: "Bearer " + token,
        },
      });
    } catch {
      // Ignore logout call failures; still clear token.
    }
  }
  clearToken();
  window.location.href = "/";
};

document.addEventListener("DOMContentLoaded", () => {
  renderAuthInfo();
});

