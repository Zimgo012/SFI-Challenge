import EmptyPanel from '../components/EmptyPanel'
import PageSection from '../components/PageSection'

export default function FleetPage() {
  return (
    <PageSection title="Fleet & Schedule" description="Inspect individual units and their assignment timelines.">
      <div className="grid gap-5 xl:grid-cols-2">
        <EmptyPanel title="Fleet units" description="Individual units and availability will appear here when fleet data is connected." />
        <EmptyPanel title="Assignment timelines" description="Unit schedules and assignments will appear here when schedule data is connected." />
      </div>
    </PageSection>
  )
}
