import { useState } from 'react'

export default function App() {
  const [count, setCount] = useState(0)

  return (
    <main className="flex min-h-screen items-center justify-center bg-base-200 p-6">
      <section className="card w-full max-w-xl bg-base-100 shadow-xl" aria-labelledby="welcome-title">
        <div className="card-body gap-6">
          <div className="badge badge-primary badge-outline">SFI Challenge</div>
          <div className="space-y-3">
            <h1 id="welcome-title" className="text-3xl font-bold">Ready to build.</h1>
            <p className="text-base-content/70">
              React, Vite, Tailwind CSS, and daisyUI are set up and ready for your next idea.
            </p>
          </div>
          <div className="flex flex-wrap gap-2" aria-label="Project technologies">
            {['React', 'Vite', 'Tailwind CSS', 'daisyUI'].map((technology) => (
              <span key={technology} className="badge badge-soft">{technology}</span>
            ))}
          </div>
          <div className="card-actions">
            <button className="btn btn-primary" onClick={() => setCount((current) => current + 1)}>
              Clicked {count} {count === 1 ? 'time' : 'times'}
            </button>
          </div>
          <p className="text-sm text-base-content/60">
            Edit <code className="rounded bg-base-200 px-1.5 py-0.5">src/App.tsx</code> to get started.
          </p>
        </div>
      </section>
    </main>
  )
}
