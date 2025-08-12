import Link from 'next/link'

export default function Home() {
  return (
    <section className="space-y-8">
      <div className="card p-8">
        <h1 className="font-display text-3xl md:text-4xl tracking-tight">Manthan — Creator Suite</h1>
        <p className="mt-3 text-neutral-300 max-w-2xl">
          From <b>logline</b> to a crisp <b>pitch pack</b>, then straight to the right buyers. Build momentum with a workflow that feels premium and fast.
        </p>
        <div className="mt-6 flex gap-3">
          <Link href="/projects/new" className="btn btn-primary">Create Project</Link>
          <Link href="/projects" className="btn btn-ghost">View Projects</Link>
        </div>
      </div>
      <div className="grid md:grid-cols-3 gap-4">
        {[
          ['AI Pitch Pack', 'Synopsis, beats, deck outline in seconds.'],
          ['Project Library', 'Your projects, neatly organized.'],
          ['Secure by Google', 'Sign in with Google.'],
        ].map((c,i)=>(
          <div key={i} className="card p-6">
            <h3 className="font-display text-lg">{c[0]}</h3>
            <p className="text-neutral-300">{c[1]}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
