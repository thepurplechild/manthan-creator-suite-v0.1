'use client'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useAuth } from '../../components/auth'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://manthan-backend-524579286496.asia-south1.run.app'

type Project = { id: string; title: string; logline: string; genre?: string; tone?: string; creator_name?: string }

export default function Projects() {
  const { user } = useAuth()
  const [data, setData] = useState<Project[] | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    ;(async () => {
      try {
       const token = await getFreshIdToken()

        const res = await fetch(`${BACKEND}/api/projects`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.ok) throw new Error(await res.text())
        setData(await res.json())
      } catch (e: any) {
        setErr(e.message || 'Failed to fetch')
      }
    })()
  }, [user])

  if (!user) {
    return (
      <main className="space-y-6">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <p className="opacity-80">
          Please <Link href="/login" className="text-indigo-300 underline">sign in</Link> to view your projects.
        </p>
      </main>
    )
  }

  return (
    <main className="space-y-6">
      <h1 className="text-2xl font-semibold">Projects</h1>
      {err && <p className="text-red-400">{err}</p>}
      <div className="grid md:grid-cols-2 gap-4">
        {data?.map(p => (
          <div key={p.id} className="card p-4">
            <h3 className="text-lg font-medium">{p.title}</h3>
            <p className="opacity-80 text-sm">{p.logline}</p>
            <p className="opacity-60 text-xs mt-2">{[p.genre, p.tone].filter(Boolean).join(' • ')}</p>
          </div>
        ))}
      </div>
    </main>
  )
}

