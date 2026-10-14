import EmptyPanel from '../components/EmptyPanel'
import PageSection from '../components/PageSection'

export default function LoadBoardPage() {
  return (
    <PageSection title="Load Board" description="Browse live fixed-rate and open-bid opportunities.">
      <div className="grid gap-5 xl:grid-cols-2">
        <EmptyPanel title="Fixed-rate opportunities" description="Fixed-rate loads will appear here when load data is connected." />
        <EmptyPanel title="Open-bid opportunities" description="Loads accepting bids will appear here when load data is connected." />
      </div>
    </PageSection>
  )
}
