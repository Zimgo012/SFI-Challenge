import EmptyPanel from '../components/EmptyPanel'
import PageSection from '../components/PageSection'

export default function ActivityPage() {
  return (
    <PageSection title="Activity" description="Review decisions, submissions, results, and errors.">
      <div className="grid gap-5 xl:grid-cols-2">
        <EmptyPanel title="Activity history" description="Decisions, submissions, results, and errors will appear here when activity data is connected." />
      </div>
    </PageSection>
  )
}
