'use client'
export const dynamic = 'force-dynamic'

import { useEffect, useMemo, useState, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useAuth } from '../../../../components/auth'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || ''
type Candidate = { id: string; text: string; meta?: any }

function DialogueInner() {
  const { user } = useAuth()
  const router = useRouter()
  const sp = useSearchParams()
  const pid = sp.get('pid') || ''
  const engine = sp.get('engine') || 'gpt-5-mini'
  const lang = sp.get('lang') || 'en'

  const [tweak, setTweak] = useState('')
  const [cands, setCands] = useState<Candidate[]|null>(null)
  const [edits, setEdits] = useState<Record<string,string>>({})
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string|null>(null)

  const canGo = useMemo(() => Boolean(pid && user), [pid, user])

  const generate = async () => {
    if (!canGo) return
    setLoading(true); setErr(null)
    try {
      const token = await user!.getIdToken(true)
      const res = await fetch(`${BACKEND}/api/stage/generate`, {
        method:'POST',
        headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` },
        body: JSON.stringify({ project_id: pid, stage: 'dialogue', tweak, engine })
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setCands(data.candidates)
      setEdits({})
    } catch (e:any) {
      setErr(e.message || 'Failed to generate dialogue passes')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { generate() }, [])

  const choose = async (id: string) => {
    try {
      const token = await user!.getIdToken(true)
      const res = await fetch(`${BACKEND}/api/stage/choose`, {
        method:'POST',
        headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` },
        body: JSON.stringify({ project_id: pid, stage: 'dialogue', chosen_id: id, edits: edits[id] || '' })
      })
    if (!res.ok) throw new Error(await res.text())
      router.push(`/projects`)
    } catch (e:any) {
      setErr(e.message || 'Failed to choose dialogue pass')
    }
  }

  if (!user) return <main className="max-w-4xl mx-auto p-6">Please sign in.</main>

  return (
    <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
      <h1 className="text-2xl font-semibold">Step 6: Dialogue Passes (3 options)</h1>

      <div className="grid md:grid-cols-3 gap-4">
        {(cands||[]).map(c => (
          <div key={c.id} className="rounded-xl bg-neutral-900/60 border border-neutral-800 p-4 flex flex-col gap-3">
            <pre className="text-sm whitespace-pre-wrap">{c.text}</pre>
            <textarea className="w-full px-3 py-2 rounded-xl bg-neutral-950 border border-neutral-800 text-sm"
                      placeholder="Tweak / edit (optional)…"
                      value={edits[c.id] || ''} onChange={e=>setEdits({...edits, [c.id]: e.target.value})}
                      rows={4}/>
            <button onClick={()=>choose(c.id)} className="px-3 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700">
              Choose this dialogue →
            </button>
          </div>
        ))}
      </div>

      <div className="rounded-xl bg-neutral-900/50 border border-neutral-800 p-4 space-y-3">
        <label className="block text-sm">Regenerate with a steering note (optional)</label>
        <input className="w-full px-3 py-2 rounded-xl bg-neutral-950 border border-neutral-800"
               value={tweak} onChange={e=>setTweak(e.target.value)} />
        <button onClick={generate} disabled={loading}
                className="px-4 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700">
          {loading ? 'Generating…' : 'Regenerate 3 dialogue passes'}
        </button>
        {err && <p className="text-red-400">{err}</p>}
      </div>
    </main>
  )
}

export default function Page() {
  return (
    <Suspense fallback={<div className="p-6">Loading…</div>}>
      <DialogueInner />
    </Suspense>
  )
}
