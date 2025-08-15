import { auth } from "./firebase";

const BASE = process.env.NEXT_PUBLIC_BACKEND_URL!;

async function getIdToken(): Promise<string | null> {
  const user = auth.currentUser;
  if (!user) return null;
  try { return await user.getIdToken(true); } catch { return null; }
}

async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers || {});
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  const idToken = await getIdToken();
  if (idToken) headers.set("Authorization", `Bearer ${idToken}`);

  const res = await fetch(`${BASE}${path}`, { ...init, headers, cache: "no-store" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status} ${res.statusText} @ ${path}\n${text}`);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

export const api = {
  get: <T=unknown>(path: string) => apiFetch(path) as Promise<T>,
  post: <T=unknown>(path: string, body?: any) =>
    apiFetch(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }) as Promise<T>,
  del: <T=unknown>(path: string) => apiFetch(path, { method: "DELETE" }) as Promise<T>,
  fetch: apiFetch,
};

