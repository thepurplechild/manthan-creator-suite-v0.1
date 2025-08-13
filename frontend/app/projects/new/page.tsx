'use client'
import Link from 'next/link'
import { useState } from 'react'
import { useAuth } from '../../../components/auth'

const BACKEND =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  'https://<YOUR-manthan-backend-URL>.a.run.app'

export default function NewProject() {
  const { user } = useAuth()
  const [title, setTitle] = useState('')
  const [logline, setLogline] = useState('')
  const [genre, setGenre] = useState('')
  const [tone, setTone] = useState('')
  const [creatorName, setCreatorName] = useState('')
  const [pitch, setPitch] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  if (!user) {
    return (
      <main className="space-y-6">
        <h1 className="text-2xl font-semibold">New Project</h1>
        <p className="opacity-80">
          Please <Link href="/login" className="text-indigo-300 underline">sign in</Link> to create a project.
        </p>
      </main>
    )
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErr(null); setLoading(true)
    try {
     const token = await getFreshIdToken()



      // create project
      const res = await fetch(`${BACKEND}/api/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title, logline, genre, tone, creator_name: creatorName }),
      })
      if (!res.ok) throw new Error(await res.text())

      // generate pitch-pack
      const gen = await fetch(`${BACKEND}/api/pitch/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title, logline, genre, tone }),
      })
      if (!gen.ok) throw new Error(await gen.text())
      const payload = await gen.json()
      setPitch(payload)
    } catch (e: any) {
      setErr(e.message || 'Failed to create project')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="space-y-8">
      <h1 className="text-2xl font-semibold">New Project</h1>
      <form onSubmit={onSubmit} className="grid gap-4 max-w-2xl">
        <input className="px-4 py-3 rounded-xl bg-neutral-900 border border-neutral-800" placeholder="Title" value={title} onChange={e=>setTitle(e.target.value)} required />
        <textarea className="px-4 py-3 rounded-xl bg-neutral-900 border border-neutral-800" placeholder="Logline" value={logline} onChange={e=>setLogline(e.target.value)} required rows={3} />
        <div className="grid md:grid-cols-2 gap-4">
          <input className="px-4 py-3 rounded-xl bg-neutral-900 border border-neutral-800" placeholder="Genre (e.g., Drama)" value={genre} onChange={e=>setGenre(e.target.value)} />
          <input className="px-4 py-3 rounded-xl bg-neutral-900 border border-neutral-800" placeholder="Tone (e.g., grounded, darkly comic)" value={tone} onChange={e=>setTone(e.target.value)} />
        </div>
        <input className="px-4 py-3 rounded-xl bg-neutral-900 border border-neutral-800" placeholder="Creator name (optional)" value={creatorName} onChange={e=>setCreatorName(e.target.value)} />
        <button disabled={loading} className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50">
          {loading ? 'Creating…' : 'Create & Generate Pitch Pack'}
        </button>
        {err && <p className="text-red-400">{err}</p>}
      </form>

      {pitch && (
        <section className="rounded-2xl p-6 bg-neutral-900/60 border border-neutral-800">
          <h2 className="text-xl font-medium mb-2">Pitch Pack</h2>
          <h3 className="text-lg font-semibold">{pitch.title}</h3>
          <p className="opacity-80 mt-1">{pitch.logline}</p>
          <h4 className="mt-4 font-medium">Synopsis</h4>
          <p className="opacity-90">{pitch.synopsis}</p>
          <h4 className="mt-4 font-medium">Beat Sheet</h4>
          <ol className="list-decimal ml-6 space-y-1">{pitch.beat_sheet?.map((b:string,i:number)=>(<li key={i}>{b}</li>))}</ol>
          <h4 className="mt-4 font-medium">Deck Outline</h4>
          <ul className="list-disc ml-6 space-y-1">{pitch.deck_outline?.map((b:string,i:number)=>(<li key={i}>{b}</li>))}</ul>
        </section>
      )}
    </main>
  )
}
