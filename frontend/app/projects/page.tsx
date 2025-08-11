'use client'
import { useEffect, useState } from 'react'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL

type Project = { id: string; title: string; logline: string; genre?: string; tone?: string; creator_name?: string }

export default function Projects() {
  const [data, setData] = useState<Project[] | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    async function run() {
      try {
        const res = await fetch(`${BACKEND}/api/projects`)
        if (!res.ok) throw new Error(await res.text())
        setData(await res.json())
      } catch (e:any) {
        setErr(e.message || 'Failed to load projects')
      }
    }
    run()
  }, [])

  return (
    <main className="space-y-6">
      <h1 className="text-2xl font-semibold">Projects</h1>
      {err && <p className="text-red-400">{err}</p>}
      <div className="grid md:grid-cols-2 gap-4">
        {data?.map(p => (
          <div key={p.id} className="rounded-xl bg-neutral-900/60 p-4 border border-neutral-800">
            <h3 className="text-lg font-medium">{p.title}</h3>
            <p className="opacity-80 text-sm">{p.logline}</p>
            <p className="opacity-60 text-xs mt-2">{[p.genre, p.tone].filter(Boolean).join(' • ')}</p>
          </div>
        ))}
      </div>
    </main>
  )
}
