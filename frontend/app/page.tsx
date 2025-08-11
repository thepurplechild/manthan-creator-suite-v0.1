import Link from 'next/link'

export default function Home() {
  return (
    <main className="space-y-8">
      <header className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold tracking-tight">Project Manthan — Creator Suite</h1>
        <nav className="flex gap-3">
          <Link href="/projects" className="px-4 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700">Projects</Link>
          <Link href="/projects/new" className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500">New Project</Link>
        </nav>
      </header>
      <section className="rounded-2xl p-6 bg-neutral-900/60 shadow">
        <h2 className="text-xl mb-2">Welcome</h2>
        <p className="opacity-80">Start by creating a project. I’ll generate a pitch-pack (synopsis, beats, deck outline) from your logline.</p>
      </section>
    </main>
  )
}
