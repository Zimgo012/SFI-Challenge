import { useEffect, useState } from 'react'
import { subscribeTerminalStatuses } from '../api/terminals'
import type { TerminalStatus, TerminalStreamState } from '../api/terminals'
import EmptyPanel from '../components/EmptyPanel'
import PageSection from '../components/PageSection'

const statusLabels: Record<TerminalStatus['status'], string> = {
  available: 'Available',
  unavailable: 'Unavailable',
  empty: 'Empty',
  attention: 'Needs attention',
  unknown: 'Unknown',
}

const statusColors: Record<TerminalStatus['status'], string> = {
  available: 'badge-success',
  unavailable: 'badge-neutral',
  empty: 'badge-ghost',
  attention: 'badge-warning',
  unknown: 'badge-info',
}

export default function TerminalsPage() {
  const [{ terminals, connection, error }, setStream] = useState<TerminalStreamState>({
    terminals: null,
    connection: 'connecting',
    error: null,
  })

  useEffect(() => {
    return subscribeTerminalStatuses(setStream)
  }, [])

  const availableUnits = terminals?.length && terminals.every((terminal) => terminal.available_units !== null)
    ? terminals.reduce((total, terminal) => total + (terminal.available_units ?? 0), 0)
    : null

  return (
    <PageSection title="Terminals" description="Compare current capacity across hubs.">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <p className="text-sm text-base-content/65">Capacity updates automatically as fleet data syncs.</p>
        <span role="status" className={`badge badge-soft ${connection === 'live' ? 'badge-success' : 'badge-warning'}`}>
          {connection === 'live' ? 'Live updates' : connection === 'connecting' ? 'Connecting…' : 'Reconnecting…'}
        </span>
      </div>

      {error && (
        <div role="alert" className="alert alert-warning">
          <div>
            <p>{error}</p>
            {terminals !== null && <p className="mt-1 text-sm">Showing the previous results. Capacity may have changed.</p>}
          </div>
        </div>
      )}

      <div aria-busy={terminals === null}>
        {terminals === null && (
          <div role="status" className="flex items-center gap-3 rounded-xl border border-base-300 bg-base-100 p-8">
            <span className="loading loading-spinner text-primary" aria-hidden="true" />
            {connection === 'reconnecting' ? 'Waiting to reconnect for terminal capacity…' : 'Loading terminal capacity…'}
          </div>
        )}

        {terminals?.length === 0 && (
          <EmptyPanel title="No terminals yet" description="Terminal capacity will appear after the first terminal sync." />
        )}

        {terminals !== null && terminals.length > 0 && (
          <div className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-3">
              {[
                { label: 'Terminals', value: terminals.length },
                { label: 'Available units', value: availableUnits ?? '—' },
                { label: 'Needs attention', value: terminals.filter((terminal) => terminal.status === 'attention').length },
              ].map((summary) => (
                <div key={summary.label} className="stat rounded-xl border border-base-300 bg-base-100">
                  <div className="stat-title">{summary.label}</div>
                  <div className="stat-value text-primary">{summary.value}</div>
                </div>
              ))}
            </div>

            <div className="overflow-x-auto rounded-xl border border-base-300 bg-base-100">
              <table className="table">
                <caption className="px-4 py-4 text-left text-sm text-base-content/65">
                  Local fleet counts compared with board availability. A dash means the count is not yet known.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Terminal</th>
                    <th scope="col">Status</th>
                    <th scope="col" className="text-right">Total units</th>
                    <th scope="col" className="text-right">Available</th>
                    <th scope="col" className="text-right">Assigned</th>
                    <th scope="col" className="text-right">Board available</th>
                  </tr>
                </thead>
                <tbody>
                  {terminals.map((terminal) => (
                    <tr key={terminal.terminal_id} className="hover:bg-base-200/60">
                      <th scope="row" className="min-w-44 font-normal">
                        <span className="font-semibold text-primary">{terminal.code}</span>
                        <p className="font-medium">{terminal.name}</p>
                        <p className="text-xs text-base-content/60">{terminal.city}, {terminal.state}</p>
                      </th>
                      <td><span className={`badge badge-soft whitespace-nowrap ${statusColors[terminal.status]}`}>{statusLabels[terminal.status]}</span></td>
                      <td className="text-right tabular-nums">{terminal.total_units ?? '—'}</td>
                      <td className="text-right font-semibold tabular-nums">{terminal.available_units ?? '—'}</td>
                      <td className="text-right tabular-nums">{terminal.assigned_units ?? '—'}</td>
                      <td className="text-right tabular-nums">{terminal.board_available_units ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </PageSection>
  )
}
