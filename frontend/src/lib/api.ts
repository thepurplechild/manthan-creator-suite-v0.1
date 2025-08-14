// frontend/src/lib/api.ts
import { auth } from "./firebase";

const BASE = process.env.NEXT_PUBLIC_BACKEND_URL!;

export async function apiFetch(path: string, init: RequestInit = {}) {
  const user = auth.currentUser;
  const idToken = user ? await user.getIdToken(true) : null;

  const headers = new Headers(init.headers || {});
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (idToken) headers.set("Authorization", `Bearer ${idToken}`);

  const res = await fetch(`${BASE}${path}`, { ...init, headers, cache: "no-store" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status} ${res.statusText}: ${text}`);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}
