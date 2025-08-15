"use client";
import { useEffect, useState } from "react";

type Status = { ok: boolean; frontend_origin: string; use_model?: boolean; autosave?: boolean };

export default function AgentHealthCard() {
  const [status, setStatus] = useState<null | Status>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const url = `${process.env.NEXT_PUBLIC_BACKEND_URL}/health/config`;
    fetch(url)
      .then(r => r.json())
      .then(setStatus)
      .catch(e => setErr(e?.message || "Cannot reach backend"));
  }, []);

  return (
    <div className="rounded-2xl p-4 shadow bg-white space-y-2">
      <h3 className="text-lg font-semibold">Agent Health</h3>
      {err && <div className="text-red-600">{err}</div>}
      {status && (
        <div className="text-sm space-y-1">
          <div>Backend reachable: <b>{status.ok ? "Yes" : "No"}</b></div>
          <div>Backend CORS expects: <code>{status.frontend_origin}</code></div>
          {"use_model" in (status || {}) && <div>Model powered: <b>{status.use_model ? "On" : "Off"}</b></div>}
          {"autosave" in (status || {}) && <div>Autosave: <b>{status.autosave ? "On" : "Off"}</b></div>}
        </div>
      )}
      {!status && !err && <div className="text-sm text-gray-500">Checking…</div>}
    </div>
  );
}
