'use client'
import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { initializeApp, getApps } from 'firebase/app'
import { getAuth, onAuthStateChanged, GoogleAuthProvider, signInWithPopup, signOut, User } from 'firebase/auth'

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY!,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN!,  // project-manthan-468609.firebaseapp.com
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID!,    // project-manthan-468609
}


if (!firebaseConfig.apiKey || !firebaseConfig.authDomain || !firebaseConfig.projectId) {
  // Helpful console hint in case envs are missing in Cloud Run
  // eslint-disable-next-line no-console
  console.error('Missing NEXT_PUBLIC_FIREBASE_* env. Check Cloud Run → manthan-frontend → Variables.')
}

const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig)
const auth = getAuth(app)
const provider = new GoogleAuthProvider()

type Ctx = {
  user: User | null
  signIn: () => Promise<void>
  signOutUser: () => Promise<void>
  getFreshIdToken: () => Promise<string | null>
  tokenInfo: { aud?: string; iss?: string } | null
}

const AuthCtx = createContext<Ctx | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [tokenInfo, setTokenInfo] = useState<{ aud?: string; iss?: string } | null>(null)

  useEffect(() => {
    return onAuthStateChanged(auth, async (u) => {
      setUser(u)
      if (u) {
        // force refresh so we never send a stale token
        const res = await u.getIdTokenResult(true)
        setTokenInfo({ aud: (res.claims as any)?.aud, iss: (res.claims as any)?.iss })
      } else {
        setTokenInfo(null)
      }
    })
  }, [])

  const signIn = async () => { await signInWithPopup(auth, provider) }
  const signOutUser = async () => { await signOut(auth) }
  const getFreshIdToken = async () => user ? await user.getIdToken(true) : null

  const value = useMemo(() => ({ user, signIn, signOutUser, getFreshIdToken, tokenInfo }), [user, tokenInfo])
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthCtx)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
