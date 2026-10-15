import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { getSimulationClock, setSimulationSpeed } from '../api/system'
import type { SimulationClock } from '../api/system'
import PageSection from '../components/PageSection'
import { timestamp } from '../utils/load-format'

const presets = [1, 10, 60, 120, 3600]

async function readClock(response: Response): Promise<SimulationClock> {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Simulator request failed (HTTP ${response.status}).`)
  }
  const clock: SimulationClock = await response.json()
  if (!Number.isFinite(clock.simulation_speed) || clock.simulation_speed < 1) throw new Error('The simulator returned an invalid clock.')
  return clock
}

export default function SettingsPage() {
  const [clock, setClock] = useState<SimulationClock | null>(null)
  const [speed, setSpeed] = useState('')
  const [loading, setLoading] = useState(import.meta.env.DEV)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const saveController = useRef<AbortController | null>(null)
  const submitting = useRef(false)

  useEffect(() => {
    if (!import.meta.env.DEV) return
    const controller = new AbortController()
    getSimulationClock({ signal: controller.signal }).then(readClock).then((data) => {
      if (!controller.signal.aborted) {
        setClock(data)
        setSpeed(String(data.simulation_speed))
        setError(null)
      }
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Unable to read the simulator clock.')
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [reload])

  useEffect(() => () => saveController.current?.abort(), [])

  async function saveSpeed(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (loading || submitting.current || !import.meta.env.DEV) return
    const value = Number(speed)
    if (!speed.trim() || !Number.isFinite(value) || value < 1 || value > 100_000) {
      setError('Enter a simulation speed between 1 and 100,000.')
      return
    }
    const controller = new AbortController()
    saveController.current = controller
    submitting.current = true
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const data = await readClock(await setSimulationSpeed(value, { signal: controller.signal }))
      if (!controller.signal.aborted) {
        setClock(data)
        setSpeed(String(data.simulation_speed))
        setMessage(`Simulation speed updated to ${data.simulation_speed.toLocaleString()}×.`)
        window.dispatchEvent(new Event('simulation-speed-updated'))
      }
    } catch (cause) {
      if (!controller.signal.aborted) {
        setError(`${cause instanceof Error ? cause.message : 'Unable to update simulation speed.'} Refresh the current speed before retrying; the change may already have reached the simulator.`)
      }
    } finally {
      submitting.current = false
      if (!controller.signal.aborted) setSaving(false)
    }
  }

  function refreshClock() {
    setLoading(true)
    setError(null)
    setMessage(null)
    setReload((value) => value + 1)
  }

  const value = Number(speed)
  const valid = !!speed.trim() && Number.isFinite(value) && value >= 1 && value <= 100_000

  return (
    <PageSection title="Settings" description="Temporary simulation controls for local testing.">
      {!import.meta.env.DEV ? (
        <p className="rounded-xl border border-base-300 bg-base-100 p-6 text-base-content/65">Simulation controls are available when running the local development server.</p>
      ) : (
        <section aria-labelledby="simulation-settings-title" className="card max-w-2xl border border-base-300 bg-base-100">
          <div className="card-body gap-6">
            <div className="flex items-start justify-between gap-4">
              <div><h2 id="simulation-settings-title" className="text-lg font-semibold">Simulation speed</h2><p className="mt-1 text-sm text-base-content/60">Control how quickly pickup, delivery, and bid timers advance.</p></div>
              <span className="badge badge-soft badge-warning">Temporary</span>
            </div>
            <div aria-busy={loading} className="grid gap-4 rounded-xl bg-base-200 p-4 sm:grid-cols-2">
              <div><p className="text-xs text-base-content/60">Current speed</p><p className="mt-1 text-2xl font-bold text-primary">{loading ? 'Loading…' : clock ? `${clock.simulation_speed.toLocaleString()}×` : 'Unavailable'}</p></div>
              <div><p className="text-xs text-base-content/60">Simulation time at last check</p><p className="mt-1 text-sm font-medium">{timestamp(clock?.sim_time_utc ?? null)}</p></div>
            </div>
            {error && <p role="alert" className="alert alert-error text-sm">{error}</p>}
            {message && <p role="status" className="alert alert-success text-sm">{message}</p>}
            <form className="space-y-4" onSubmit={(event) => void saveSpeed(event)}>
              <label htmlFor="simulation-speed" className="block text-sm font-medium">Speed multiplier</label>
              <input id="simulation-speed" className="input input-bordered w-full" type="number" min="1" max="100000" step="any" required value={speed} disabled={loading || saving} onChange={(event) => setSpeed(event.target.value)} aria-describedby="simulation-speed-help" />
              <p id="simulation-speed-help" className="text-xs text-base-content/60">1× is real time. At 60×, one real second advances one simulated minute.</p>
              <div className="flex flex-wrap gap-2" aria-label="Simulation speed presets">
                {presets.map((preset) => <button key={preset} type="button" className={`btn btn-sm ${Number(speed) === preset ? 'btn-primary' : 'btn-outline'}`} disabled={loading || saving} aria-pressed={Number(speed) === preset} onClick={() => setSpeed(String(preset))}>{preset.toLocaleString()}×</button>)}
              </div>
              <p className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm">Changing speed also resets simulation time to the current real time. New order arrival frequency stays the same.</p>
              <div className="flex flex-wrap gap-3">
                <button type="submit" className="btn btn-primary btn-sm" disabled={!valid || !clock || loading || saving || value === clock.simulation_speed}>
                  {saving && <span className="loading loading-spinner loading-xs" aria-hidden="true" />}{saving ? 'Applying…' : 'Apply speed'}
                </button>
                <button type="button" className="btn btn-ghost btn-sm" disabled={loading || saving} onClick={refreshClock}>{loading ? 'Loading…' : 'Refresh current speed'}</button>
              </div>
            </form>
            <p className="text-xs text-base-content/60">Other pages will reflect the new speed after the dispatcher receives its next clock sync.</p>
          </div>
        </section>
      )}
    </PageSection>
  )
}
