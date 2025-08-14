'use client'
export const dynamic = 'force-dynamic'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '../../../../components/auth'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || ''
type Candidate = { id: string; text: string; meta?: any }

export default function Page() {
  const { user } = useAuth()
  const router = useRouter()

  const [pid, setPid] = useState('')
  const [engine, setEngine] = useState('gpt-5-mini')
  const [lang, setLang] = useState('en')

  const [tweak, setTweak] = useState('')
  const [cands, setCands] = useState<Candidate[]|null>(null)
  const [edits, setEdits] = useState<Record<string,string>>({})
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string|null>(null)

  useEffect(() => {
    const qs = new URLSearchParams(window.location.search)
    setPid(qs.get('pid') || '')
    setEngine(qs.get('engine') || 'gpt-5-mini')
    setLang(qs.get('lang') || 'en')
  }, [])

  const canGo = useMemo(() => Boolean(pid && user), [pid, user])

  const generate = async () => {
    if (!canGo) return
    setLoading(true); setErr(null)
    try {
      const token = await user!.getIdToken(true)
      const res = await fetch(`${BACKEND}/api/stage/generate`, {
        method:'POST',
        headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` },
        body: JSON.stringify({ project_id: pid, stage: 'outline', tweak, engine })
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setCands(data.candidates)
      setEdits({})
    } catch (e:any) {
      setErr(e.message || 'Failed to generate outlines')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { generate() }, [canGo])

  const choose = async (id: string) => {
    try {
      const token = await user!.getIdToken(true)
      const res = await fetch(`${BACKEND}/api/stage/choose`, {
        method:'POST',
        headers:{ 'Content-Type':'application/json', Authorization:`Bearer ${token}` },
        body: JSON.stringify({ project_id: pid, stage: 'outline', chosen_id: id, edits: edits[id] || '' })
      })
      if (!res.ok) throw new Error(await res.text())
      const nextQs = new URLSearchParams({ pid, engine, lang })
      router.push(`/flows/new/onepager?${nextQs.toString()}`)
    } catch (e:any) {
      setErr(e.message || 'Failed to choose outline')
    }
  }

  if (!user) return <main className="max-w-4xl mx-auto p-6">Please sign in.</main>

  return (
    <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
      <h1 className="text-2xl font-semibold">Step 2: Outlines (3 options)</h1>

      <div className="grid md:grid-cols-3 gap-4">
        {(cands||[]).map(c => (
          <div key={c.id} className="rounded-xl bg-neutral-900/60 border border-neutral-800 p-4 flex flex-col gap-3">
            <div className="text-sm whites
