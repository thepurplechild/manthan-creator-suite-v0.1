'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useAuth } from '../../../components/auth'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL!

type PitchPack = {
  title: string
  logline: string
  synopsis: string
  beat_sheet: string[]
  deck_outline: string[]
}

export default function NewProjectPage() {
  const { user } = useAuth()

  const [title, setTitle] = useState('')
  const [logline, setLogline] = useState('')
  const [genre, setGenre] = useState('')
  const [tone, setTone] = useState('')

  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pitch, setPitch] = useState<PitchPack | null>(null)

  if (!BACKEND) {
    return (
      <main className="max-w-4xl mx-auto px-6 py-8 space-y-4">
        <h1 className="text-2xl font-semibold">New Project</h1>
        <p className="text-red-400">
          NEXT_PUBLIC_BACKEND_URL is not set on the frontend service.
        </p>
      </main>
    )
  }

  if (!user) {
    return (
      <main className="max-w-4xl mx-auto px-6 py-8 space-y-4">
        <h1 className="text-2xl font-semibold">New Project</h1>
        <p className="opacity-80">
          Please <Link href="/login" className="text-indigo-300 underline">sign in</Link> to create a project.
        </p>
      </main>
    )
  }

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setPitch(null)
    try {
      setSaving(true)
      const token = await user.getIdToken(true) // << force fresh token
      const res = await fetch(`${BACKEND}/api/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title,
          logline,
          genre: genre || undefined,
          tone: tone || undefined,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
    } catch (e: any) {
      setError(e?.message || 'Failed to create project')
      return
    } finally {
      setSaving(false)
    }

    // After saving, immediately generate a pitch pack
    try {
      setGenerating(true)
      const token = await user.getIdToken(true) // << force fresh token (again)
      const res = await fetch(`${BACKEND}/api/pitch/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title,
          logline,
          genre: genre || undefined,
          tone: tone || undefined,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = (await res.json()) as PitchPack
      setPitch(data)
    } catch (e: any) {
      setError(e?.message || 'Failed to generate pitch pack')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">New Project</h1>
        <Link href="/projects" className="px-3 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700">
          Back to Projects
        </Link>
      </div>

      <form onSubmit={onCreate} className="grid gap-4 max-w-3xl">
        <div>
          <label className="block text-sm mb-1">Title</label>
          <input
            className="w-full px-3 py-2 rounded-xl bg-neutral-900 border border-neutral-800"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            minLength={2}
            maxLength={120}
            placeholder="e.g., Dhundh"
          />
        </div>

        <div>
          <label className="block text-sm mb-1">Logline</label>
          <textarea
            className="w-full px-3 py-2 rounded-xl bg-neutral-900 border border-neutral-800"
            value={logline}
            onChange={(e) => setLogline(e.target.value)}
            required
            minLength={5}
            maxLength={400}
            rows={3}
            placeholder="One-sentence premise that the whole pitch will follow."
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm mb-1">Genre (optional)</label>
            <input
              className="w-full px-3 py-2 rounded-xl bg-neutral-900 border border-neutral-800"
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
              placeholder="Drama / Thriller / Comedy …"
            />
          </div>
          <div>
            <label className="block text-sm mb-1">Tone (optional)</label>
            <input
              className="w-full px-3 py-2 rounded-xl bg-neutral-900 border border-neutral-800"
              value={tone}
              onChange={(e) => setTone(e.target.value)}
              placeholder="Grounded, character-driven …"
            />
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={saving || generating}
            className="px-4 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700 disabled:opacity-60"
          >
            {saving ? 'Saving…' : generating ? 'Generating…' : 'Create & Generate'}
          </button>
          {error && <span className="text-red-400">{error}</span>}
        </div>
      </form>

      {pitch && (
        <section className="mt-6 max-w-3xl space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-medium">Pitch Pack</h2>
          </div>
          <div className="rounded-xl bg-neutral-900/60 border border-neutral-800 p-4 space-y-3">
            <div>
              <h3 className="text-lg font-semibold">{pitch.title}</h3>
              <p className="opacity-80">{pitch.logline}</p>
            </div>

            <div>
              <h4 className="font-medium mb-1">Synopsis</h4>
              <p className="opacity-80 whitespace-pre-wrap">{pitch.synopsis}</p>
            </div>

            <div>
              <h4 className="font-medium mb-1">Beat Sheet</h4>
              <ol className="list-decimal pl-5 opacity-90 space-y-1">
                {pitch.beat_sheet.map((b, i) => <li key={i}>{b}</li>)}
              </ol>
            </div>

            <div>
              <h4 className="font-medium mb-1">Deck Outline</h4>
              <ul className="list-disc pl-5 opacity-90 space-y-1">
                {pitch.deck_outline.map((b, i) => <li key={i}>{b}</li>)}
              </ul>
            </div>
          </div>
        </section>
      )}
    </main>
  )
}

