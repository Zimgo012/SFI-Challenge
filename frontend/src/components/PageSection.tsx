import type { ReactNode } from 'react'

type PageSectionProps = {
  title: string
  description: string
  children: ReactNode
}

export default function PageSection({ title, description, children }: PageSectionProps) {
  return (
    <section aria-labelledby="page-title" className="space-y-8">
      <div className="space-y-2">
        <h1 id="page-title" className="text-3xl font-bold tracking-tight">{title}</h1>
        <p className="max-w-3xl text-base-content/65">{description}</p>
      </div>
      {children}
    </section>
  )
}
