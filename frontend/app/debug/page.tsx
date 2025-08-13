'use client'
import { useEffect, useState } from 'react'
import { useAuth } from '../../components/auth'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL!

export default function DebugPage() {
  const { user } = useAuth()
  const [claims, setClaims] = useState<any>(null)
  const [resp, setResp] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    ;(async () => {
      try {
        const t = await user.getIdToken(true)
        const b64 = t.split('.')[1]; const pad = '='.repeat((4 - b64.length % 4) % 4)
        const c = JSON.parse(atob((b64 + pad).replace(/-/g,'+').replace(/_/g,'/')))
        setClaims({ aud: c.aud, iss: c.iss, sub: c.sub })

        const r = await fetch(`${BACKEND}/api/debug/token`, { headers: { Authorization: 'Bearer ' + t }})
        setResp({ status: r.status, body: await r.text() })
      } catch (e:any) { setErr(e.message) }
    })()
  }, [user])

  return (
    <main className="max-w-2xl mx-auto p-6 space-y-4">
      <h1 className="text-xl font-semibold">Auth Debug</h1>
      {!user && <p>Sign in on <a href="/login" className="underline">/login</a> first.</p>}
      {err && <pre className="text-red-400">{err}</pre>}
      {claims && <pre className="bg-neutral-900 p-3 rounded">{JSON.stringify(claims, null, 2)}</pre>}
      {resp && <pre className="bg-neutral-900 p-3 rounded">{JSON.stringify(resp, null, 2)}</pre>}
    </main>
  )
}
