'use client'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useAuth } from '../../components/auth'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL!

type Project = {
  id: string
  title: string
  logline: string
  genre?: string
  tone?: string
  creator_name?: string
}

export default function ProjectsPage() {
  const { user } = useAuth()
  const [projects, setProjects] = useState<Project[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!user || !BACKEND) return
    ;(async () => {
      setLoading(true)
      setErr(null)
      try {
        const token = await user.getIdToken(true) // << force fresh token
        const res = await fetch(`${BACKEND}/api/projects`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.ok) throw new Error(await res.text())
        setProjects(await res.json())
      } catch (e: any) {
        setErr(e?.message || 'Failed to load projects')
      } finally {
        setLoading(false)
      }
    })()
  }, [user])

  if (!BACKEND) {
    return (
      <main className="max-w-4xl mx-auto px-6 py-8 space-y-4">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <p className="text-red-400">
          NEXT_PUBLIC_BACKEND_URL is not set on the frontend service.
        </p>
      </main>
    )
  }

  if (!user) {
    return (
      <main className="max-w-4xl mx-auto px-6 py-8 space-y-4">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <p className="opacity-80">
          Please <Link href="/login" className="text-indigo-300 underline">sign in</Link> to view your projects.
        </p>
      </main>
    )
  }

  return (
    <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <Link href="/projects/new" className="px-3 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700">
          New Project
        </Link>
      </div>

      {loading && <p className="opacity-70">Loading…</p>}
      {err && <p className="text-red-400 whitespace-pre-wrap">{err}</p>}

      <div className="grid md:grid-cols-2 gap-4">
        {projects?.map((p) => (
          <div key={p.id} className="rounded-xl bg-neutral-900/60 p-4 border border-neutral-800">
            <h3 className="text-lg font-medium">{p.title}</h3>
            <p className="opacity-80 text-sm">{p.logline}</p>
            <p className="opacity-60 text-xs mt-2">{[p.genre, p.tone].filter(Boolean).join(' • ')}</p>
          </div>
        ))}
        {!loading && !err && (projects?.length ?? 0) === 0 && (
          <p className="opacity-70">No projects yet. <Link href="/projects/new" className="underline">Create one</Link>.</p>
        )}
      </div>
    </main>
  )
}

