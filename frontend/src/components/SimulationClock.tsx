import { useEffect, useState } from 'react'
import { getSimulationClock, getSystemStatus } from '../api/system'
import type { SimulationClock as BoardClock, SystemStatus } from '../api/system'
import { createClockSample, simulationTime } from '../utils/simulation-clock'
import type { ClockSample } from '../utils/simulation-clock'

const dateFormat = new Intl.DateTimeFormat('en-CA', { timeZone: 'UTC', year: 'numeric', month: 'short', day: 'numeric' })
const timeFormat = new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })

export default function SimulationClock() {
  const [sample, setSample] = useState<ClockSample | null>(null)
  const [now, setNow] = useState(() => performance.now())
  const [syncError, setSyncError] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    let disposed = false
    let syncing = false
    let queued = false
    let timer: ReturnType<typeof setTimeout> | undefined

    async function readSample(): Promise<ClockSample> {
      if (import.meta.env.DEV) {
        try {
          const response = await getSimulationClock({ signal: controller.signal })
          if (response.ok) {
            const clock: BoardClock = await response.json()
            const value = createClockSample(clock.sim_time_utc, clock.simulation_speed, performance.now())
            if (value) return value
          }
        } catch {
          if (controller.signal.aborted) throw new Error('Clock read cancelled')
          // Fall back to the dispatcher when the temporary simulator proxy is unavailable.
        }
      }
      const response = await getSystemStatus({ signal: controller.signal })
      if (!response.ok) throw new Error('Unable to sync simulation clock')
      const system: SystemStatus = await response.json()
      const value = createClockSample(system.sim_time_utc, system.simulation_speed, performance.now())
      if (!value) throw new Error('Simulation clock has not synced yet')
      return value
    }

    async function sync() {
      if (disposed) return
      if (syncing) { queued = true; return }
      clearTimeout(timer)
      syncing = true
      try {
        const value = await readSample()
        if (!disposed) {
          setSample(value)
          setNow(performance.now())
          setSyncError(false)
        }
      } catch {
        if (!disposed) setSyncError(true)
      } finally {
        syncing = false
        if (!disposed) {
          setLoading(false)
          if (queued) { queued = false; void sync() }
          else timer = setTimeout(() => void sync(), 10_000)
        }
      }
    }

    const refresh = () => { void sync() }
    const onVisible = () => { if (document.visibilityState === 'visible') refresh() }
    const tick = setInterval(() => setNow(performance.now()), 1000)
    window.addEventListener('simulation-speed-updated', refresh)
    document.addEventListener('visibilitychange', onVisible)
    void sync()
    return () => {
      disposed = true
      controller.abort()
      clearTimeout(timer)
      clearInterval(tick)
      window.removeEventListener('simulation-speed-updated', refresh)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [])

  const time = simulationTime(sample, now)
  const date = time === null ? null : new Date(time)

  return (
    <div role="timer" aria-live="off" aria-label="Simulation clock" className="shrink-0 leading-tight" title={syncError ? 'Clock sync delayed; showing the last known estimate.' : 'Simulation time in UTC. Resyncs automatically.'}>
      <div className="mb-1 flex items-center gap-2 text-[10px] font-medium uppercase tracking-wide text-base-content/60">
        <span aria-hidden="true" className={`size-1.5 rounded-full ${syncError ? 'bg-warning' : date ? 'bg-success' : 'bg-base-content/30'}`} />
        <span>Simulation {sample ? `· ${sample.speed.toLocaleString()}×` : ''}</span>
        {syncError && date && <span className="normal-case tracking-normal">Sync delayed</span>}
      </div>
      {date ? (
        <time dateTime={date.toISOString()} className="block whitespace-nowrap text-xs font-semibold tabular-nums text-base-content sm:text-sm">
          {dateFormat.format(date)} · {timeFormat.format(date)} <span className="font-normal text-base-content/60">UTC</span>
        </time>
      ) : <p className="text-xs text-base-content/60">{loading ? 'Syncing clock…' : 'Clock unavailable'}</p>}
    </div>
  )
}
