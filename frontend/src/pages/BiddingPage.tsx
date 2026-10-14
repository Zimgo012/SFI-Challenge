import EmptyPanel from '../components/EmptyPanel'
import PageSection from '../components/PageSection'

export default function BiddingPage() {
  return (
    <PageSection title="Bidding" description="Evaluate open-bid opportunities and track submitted bids.">
      <div className="grid gap-5 xl:grid-cols-2">
        <EmptyPanel title="Opportunities to evaluate" description="Open-bid opportunities will appear here when bidding data is connected." />
        <EmptyPanel title="Submitted bids" description="Bid submissions and their results will appear here when bidding data is connected." />
      </div>
    </PageSection>
  )
}
