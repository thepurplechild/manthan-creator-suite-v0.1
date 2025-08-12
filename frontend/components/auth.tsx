'use client'
import { createContext, useContext, useEffect, useState } from 'react'
import { auth, googleProvider } from '../lib/firebase'
import { onAuthStateChanged, signInWithPopup, signOut, User } from 'firebase/auth'

type Ctx = { user: User | null; signIn: () => Promise<void>; signOutUser: () => Promise<void> }
const AuthCtx = createContext<Ctx>({ user: null, signIn: async()=>{}, signOutUser: async()=>{} })

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  useEffect(() => onAuthStateChanged(auth, setUser), [])
  async function signIn() { await signInWithPopup(auth, googleProvider) }
  async function signOutUser() { await signOut(auth) }
  return <AuthCtx.Provider value={{ user, signIn, signOutUser }}>{children}</AuthCtx.Provider>
}
export function useAuth() { return useContext(AuthCtx) }
