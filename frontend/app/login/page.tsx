'use client'
import { useAuth } from '../../components/auth'
import Link from 'next/link'

export default function Login() {
  const { user, signIn, signOutUser } = useAuth()
  return (
    <main className="space-y-6">
      <h1 className="text-2xl font-semibold">Sign in</h1>
      {!user ? (
        <button onClick={signIn} className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500">
          Continue with Google
        </button>
      ) : (
        <div className="space-y-4">
          <p className="opacity-80">Signed in as <b>{user.email}</b></p>
          <div className="flex gap-3">
            <Link href="/projects" className="px-4 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700">Go to Projects</Link>
            <button onClick={signOutUser} className="px-4 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700">Sign out</button>
          </div>
        </div>
      )}
    </main>
  )
}
