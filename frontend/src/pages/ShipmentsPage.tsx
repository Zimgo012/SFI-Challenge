import EmptyPanel from '../components/EmptyPanel'
import PageSection from '../components/PageSection'

export default function ShipmentsPage() {
  return (
    <PageSection title="Shipments" description="Track confirmed bookings through delivery.">
      <div className="grid gap-5 xl:grid-cols-2">
        <EmptyPanel title="Confirmed bookings" description="Shipment progress and delivery status will appear here when shipment data is connected." />
      </div>
    </PageSection>
  )
}
