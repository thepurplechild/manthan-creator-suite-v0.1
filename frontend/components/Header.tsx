'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from './auth'
import { Logo } from './Logo'

const NavLink = ({ href, children }: { href: string; children: React.ReactNode }) => {
  const pathname = usePathname()
  const active = pathname === href
  return (
    <Link
      href={href}
      className={`px-3 py-2 rounded-xl ${active ? 'bg-neutral-800 text-white' : 'text-neutral-300 hover:bg-neutral-800/60'}`}
      aria-current={active ? 'page' : undefined}
    >
      {children}
    </Link>
  )
}

export function Header() {
  const { user, signIn, signOutUser } = useAuth()
  return (
    <header className="sticky top-0 z-40 border-b border-border/80 backdrop-blur bg-[#0B0B10]/70">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          {/* Change variant to 'flow' or 'mono' if you prefer */}
          <Logo size={28} variant="sharp" />
          <span className="hidden sm:inline text-sm text-neutral-400">Creator Suite</span>
        </Link>
        <nav className="flex items-center gap-1">
          <NavLink href="/projects">Projects</NavLink>
          <NavLink href="/projects/new">New</NavLink>
          {!user ? (
            <Link href="/login" className="btn btn-primary ml-2">Sign in</Link>
          ) : (
            <button onClick={signOutUser} className="btn btn-ghost ml-2">Sign out</button>
          )}
        </nav>
      </div>
    </header>
  )
}
