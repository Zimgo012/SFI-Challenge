import { Link } from 'react-router'
import PageSection from '../components/PageSection'

const summaries = [
  { title: 'Live opportunities', path: '/loads', description: 'Open fixed-rate offers and bid opportunities.' },
  { title: 'Fleet capacity', path: '/terminals', description: 'Available capacity across your hubs.' },
  { title: 'Pending bids', path: '/bids', description: 'Submitted bids awaiting a result.' },
  { title: 'Active shipments', path: '/shipments', description: 'Confirmed bookings through delivery.' },
] as const

export default function DashboardPage() {
  return (
    <PageSection title="Dashboard" description="Summary of live opportunities, fleet capacity, pending bids, and active shipments.">
      <div className="grid gap-5 sm:grid-cols-2">
        {summaries.map((summary) => (
          <article key={summary.path} className="card border border-base-300 bg-base-100">
            <div className="card-body">
              <h2 className="card-title text-lg">{summary.title}</h2>
              <p className="text-3xl font-semibold" aria-label="Data unavailable">—</p>
              <p className="text-sm text-base-content/60">{summary.description}</p>
              <div className="card-actions mt-3">
                <Link to={summary.path} className="link link-primary">View {summary.title.toLowerCase()}</Link>
              </div>
            </div>
          </article>
        ))}
      </div>
      <p className="text-sm text-base-content/60">Summary data will appear when operations data is connected.</p>
    </PageSection>
  )
}
