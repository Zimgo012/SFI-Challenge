import EmptyPanel from '../components/EmptyPanel'
import PageSection from '../components/PageSection'

export default function TerminalsPage() {
  return (
    <PageSection title="Terminals" description="Compare current capacity across hubs.">
      <div className="grid gap-5 xl:grid-cols-2">
        <EmptyPanel title="Hub capacity" description="Terminal capacity comparisons will appear here when terminal data is connected." />
      </div>
    </PageSection>
  )
}
