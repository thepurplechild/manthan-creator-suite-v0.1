"use client";
import { useState } from "react";
import { runCreatorAgent } from "@/lib/agents";

type Idea = { title: string; logline: string; genre?: string; tone?: string };

export default function AgentButton({ idea }: { idea: Idea }) {
  const [loading, setLoading] = useState(false);
  const [pack, setPack] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  async function go() {
    setLoading(true);
    setErr(null);
    try {
      const p = await runCreatorAgent(idea);
      setPack(p);
    } catch (e: any) {
      setErr(e?.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <button onClick={go} disabled={loading} className="px-4 py-2 rounded-2xl shadow bg-black text-white">
        {loading ? "Generating…" : "Generate Pitch Pack"}
      </button>

      {err && <div className="text-red-600">{err}</div>}

      {pack && (
        <div className="grid gap-3 rounded-2xl p-4 shadow bg-white">
          <div className="flex items-center gap-3">
            <h3 className="text-xl font-semibold">Outline</h3>
            {pack.quality && (
              <span className="px-3 py-1 rounded-full border text-sm">
                Quality: {pack.quality.label} ({pack.quality.score})
              </span>
            )}
          </div>
          <ul className="list-disc pl-5">{pack.outline.map((o: string, i: number) => <li key={i}>{o}</li>)}</ul>

          <h3 className="text-xl font-semibold mt-4">One-Pager</h3>
          <pre className="whitespace-pre-wrap">{pack.one_pager}</pre>

          <h3 className="text-xl font-semibold mt-4">Deck Sections</h3>
          <div className="flex flex-wrap gap-2">
            {pack.deck_outline.map((d: string) => (
              <span key={d} className="px-3 py-1 rounded-full border">{d}</span>
            ))}
          </div>

          {pack.doc_id && (
            <div className="text-xs text-gray-600 mt-2">Saved as: <code>{pack.doc_id}</code> (Firestore)</div>
          )}
          {pack.quality?.reasons?.length > 0 && (
            <div className="text-sm mt-2">
              <div className="font-medium">Suggestions:</div>
              <ul className="list-disc pl-5">
                {pack.quality.reasons.map((r: string, i: number) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
