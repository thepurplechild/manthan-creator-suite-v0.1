'use client'
export const dynamic = 'force-dynamic'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '../../../../components/auth'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || ''

export default function Page() {
  const { user } = useAuth()
  const router = useRouter()

  const [title, setTitle] = useState('')
  const [logline, setLogline] = useState('')
  const [genre, setGenre] = useState('Drama')
  const [language, setLanguage] = useState<'en'|'hi'|'ta'|'te'|'bn'|'mr'>('en')
  const [engine, setEngine] = useState<'gpt-5-mini'|'gpt-5'|'manthan-lora'>('gpt-5-mini')
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string|null>(null)

  if (!user) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-8 space-y-4">
        <h1 className="text-2xl font-semibold">Start a New Project</h1>
        <p>Please <Link href="/login" className="underline">sign in</Link> first.</p>
      </main>
    )
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErr(null); setSaving(true)
    try {
      const token = await user.getIdToken(true)
      const res = await fetch(`${BACKEND}/api/projects`, {
        method: 'POST',
        headers: { 'Content-Type':'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ title, logline, genre, tone: '', creator_name: user.displayName || '' })
      })
      if (!res.ok) throw new Error(await res.text())
      const proj = await res.json()
      const qs = new URLSearchParams({ pid: proj.id, engine, lang: language })
      router.push(`/flows/new/outlines?${qs.toString()}`)
    } catch (e:any) {
      setErr(e.message || 'Failed to create project')
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="max-w-3xl mx-auto px-6 py-8 space-y-6">
      <h1 className="text-2xl font-semibold">New Project — Step 1: Idea</h1>

      <form onSubmit={onSubmit} className="grid gap-4">
        <div>
          <label className="block text-sm mb-1">Title</label>
          <input className="w-full px-3 py-2 rounded-xl bg-neutral-900 border border-neutral-800"
                 required minLength={2} maxLength={120}
                 value={title} onChange={e=>setTitle(e.target.value)} placeholder="e.g., Dhundh" />
        </div>

        <div>
          <label className="block text-sm mb-1">Tagline / Logline</label>
          <textarea className="w-full px-3 py-2 rounded-xl bg-neutral-900 border border-neutral-800"
                    rows={3} required minLength={5} maxLength={400}
                    value={logline} onChange={e=>setLogline(e.target.value)}
                    placeholder="One-sentence premise the whole piece will follow." />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm mb-1">Genre</label>
            <input className="w-full px-3 py-2 rounded-xl bg-neutral-900 border border-neutral-800"
                   value={genre} onChange={e=>setGenre(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm mb-1">Language</label>
            <select className="w-full px-3 py-2 rounded-xl bg-neutral-900 border border-neutral-800"
                    value={language} onChange={e=>setLanguage(e.target.value as any)}>
              <option value="en">English</option><option value="hi">Hindi</option>
              <option value="ta">Tamil</option><option value="te">Telugu</option>
              <option value="bn">Bengali</option><option value="mr">Marathi</option>
            </select>
          </div>
          <div>
            <label className="block text-sm mb-1">Engine</label>
            <select className="w-full px-3 py-2 rounded-xl bg-neutral-900 border border-neutral-800"
                    value={engine} onChange={e=>setEngine(e.target.value as any)}>
              <option value="gpt-5-mini">GPT-5 Mini (fast)</option>
              <option value="gpt-5">GPT-5 (richer)</option>
              <option value="manthan-lora">Manthan LoRA (stage-tuned)</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button disabled={saving} className="px-4 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700">
            {saving ? 'Creating…' : 'Continue → Outlines'}
          </button>
          {err && <span className="text-red-400">{err}</span>}
        </div>
      </form>
    </main>
  )
}
