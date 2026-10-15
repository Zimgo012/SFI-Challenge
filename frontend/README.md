# SFI Challenge frontend

React with TypeScript, Vite, Tailwind CSS, and daisyUI.

## Getting started

```sh
npm install
npm run dev
```

Open the local URL printed by Vite. `/` redirects to `/dashboard`.

## Pages and navigation

| Page | Route | Purpose |
| --- | --- | --- |
| Dashboard | `/dashboard` | Summary of bid opportunities, fleet capacity, pending bids, and active shipments. |
| Load Board | `/loads` | Live cards for open orders to bid on. |
| Bid Logs | `/bids` | Review and sort non-open bid orders, with details in a centered dialog. |
| Terminals | `/terminals` | Compare current capacity across hubs. |
| Fleet & Schedule | `/fleet` | Inspect individual units and assignment timelines. |
| Shipments | `/shipments` | Track confirmed bookings through delivery. |
| Activity | `/activity` | Review decisions, submissions, results, and errors. |
| Settings | `/settings` | Temporarily adjust simulator speed during local development. |

Page components live in `src/pages/`. `src/layouts/AppLayout.tsx` provides
shared navigation with active states; `src/config/navigation.ts` defines its
labels and links. `src/App.tsx` declares the routes using
[React Router](https://reactrouter.com/start/declarative/routing).
Unknown URLs show a page-not-found screen. Page content is a scaffold awaiting
backend data; dashboard values are unavailable rather than simulated counts.
The Terminals page subscribes to `/api/terminals/status/ws` and displays hub
status, local/board capacity, discrepancies, and sync times. Snapshots, updates,
and heartbeats replace the full list automatically. The page shows connection
status, preserves previous results during outages, and reconnects with a
1–30 second backoff. Missing heartbeats trigger reconnection after 45 seconds.
Connections and retry timers are cleaned up when leaving the page.

Fleet & Schedule loads the complete paginated fleet roster, simulation status,
and `/api/fleet/projections?at=<simulation-time>`. It shows availability counts,
unit/driver search, hub/status filters, and a roster with 20 units per page.
View schedule opens a centered, scrollable dialog with the unit's confirmed assignment, projected
availability, current/next hubs, coordinates, and a chronological delivery
timeline. The dialog supports close buttons, Escape and backdrop dismissal,
and continues receiving live updates while open. Timeline phases use simulation time, with unknown timestamps and
unresolved submissions shown explicitly. The projection schema exposes bookings
since the latest fleet snapshot, rather than a complete assignment archive.

Fleet data loads immediately and refreshes on terminal and order WebSocket
events, including heartbeats. Requests are serialized and event bursts coalesce
into one follow-up refresh. The selected unit and filters persist during updates.
Leaving the page closes both streams and cancels outstanding requests.

Shipments loads every page from `/api/shipments` and then uses full order
WebSocket snapshots for live updates. It includes only board-present accepted,
in-transit, and completed bookings, covering fixed-rate acceptances and winning
bids. Pending bids and unconfirmed offers are excluded. Summary counts, route
and unit search, status filters, date sorting, estimated cost, and 20-row
pagination support tracking. Delivery-overdue indicators use the simulation
clock and never infer completion from scheduled dates.

More information opens a centered read-only shipment dialog with lifecycle
steps, route/pricing details, the confirmed assignment, and assignment history
from the order detail API. Details refresh on live updates. Disconnects retain
previous shipments; cleanup closes the stream and aborts reads. Late initial
HTTP responses cannot overwrite newer WebSocket snapshots.

Activity reads `/api/activity` using server-side pagination of 20 events, newest
recorded time first. Exact order-ID and event-type filters apply across the
complete history without downloading every page. Suggested event types cover
submissions, lifecycle changes, assignments, discrepancies, and sync errors;
custom exact event types can also be entered. Apply filters or Reset starts at
page one. A centered details dialog shows the full message, identifiers,
recorded/simulation timestamps, and structured context.

Activity loads immediately and refreshes its current page on terminal/order
WebSocket events and heartbeats. Burst events queue one follow-up read. Errors
retain previous results and can be retried manually; page/filter changes and
leaving the route abort requests and close streams. The backend has no
dedicated Activity WebSocket, so event-only changes appear by the next upstream
heartbeat even when there is no order or terminal change.

Settings is a temporary local-development page with a current speed/clock readout,
speed presets, and a custom multiplier from 1 to 100,000. Changes are sent only
when Apply speed is selected. The board's `POST /simulation/clock` also resets
its simulation time to current real time; it does not change the wall-clock
arrival frequency of new orders. Other pages reflect the new speed after the
dispatcher ingests the next clock sample.

Set `SIMULATION_API_URL` in `.env` to the simulator origin (default
`http://127.0.0.1:8087`, matching the local dispatcher configuration). Vite
proxies `/__simulation/clock` to `/simulation/clock` on that origin, keeping
simulator controls separate from dispatcher requests. Restart Vite after
changing this value. This server-side variable is not exposed as a Vite client
environment variable. Production builds show the temporary controls as
unavailable. Settings does not change the dispatcher database directly.

The shared sticky header displays a ticking simulation clock in UTC with its
speed multiplier. It advances using monotonic elapsed time and reported speed,
resyncing every 10 seconds and when returning to the tab. Local demos read the
simulator clock, with dispatcher status as fallback; production uses dispatcher
status. Settings speed changes trigger immediate resynchronization. Failed
reads retain the last estimate with a sync-delayed indicator.

The Load Board subscribes to `/api/loads/ws?order_type=all&status=open` and
shows open fixed-rate and open-bid opportunities. The order-type selector filters
between both types, fixed rate, and open bid without reconnecting. Each card
labels its type; fixed-rate cards also show the offered payout. Orders disappear
as they expire or change status.
Snapshots, updates, and heartbeats replace the complete result set, including
removing orders that no longer match. Compact cards show pickup/delivery
locations, distance, cargo weight, pickup time, delivery time, and offer expiry.
Accept/decline controls use a dating-card layout. For open-bid orders, Accept
opens a profit analyzer; only submitting its form sends a bid. Every open-bid
card also has an Analyze profit link.
The analyzer uses a wide panel with margin controls and key profit figures beside
Economics and Order details tabs. Compact eligibility checks appear below the margin controls. Its submit button stays visible
at the bottom; smaller screens stack the sections above that footer.
The percentage input and slider calculate
the bid from selected-unit total cost, rounded up to cents; a manual bid can
override this target. Read-only cost previews show loaded/deadhead costs, gross
profit, actual margin, minimum profitable bid, and dispatch eligibility. Unknown
costs stay unknown. Changing the bid or receiving a new order snapshot invalidates
the previous preview; submission requires a matching eligible evaluation. Bid
amounts accept up to 16 whole digits and two decimal places. For fixed-rate offers,
Accept submits the acceptance directly. Decline submits the
documented decline action. Expired orders and disconnected streams disable
submissions. More information opens a sliding right-side dialog with pricing,
costs, assignment, location, and sync information, keyboard focus trapping,
Escape/backdrop dismissal, and reduced-motion support. Countdown
values are labeled as simulated seconds at the last update. Disconnects retain
previous results with a warning and reconnect automatically; leaving the page
closes the connection and cancels timers.

Booking submissions disable duplicate actions and preserve `sync_pending`
success. Uncertain failures are not retried automatically; Check status reads
the order detail and only re-enables an open order after recorded failed actions
are reconciled. Successful bids appear in Bid Logs; they are not confirmed bookings.

Bid Logs combines `/api/bids` with all pages of fixed-rate and open-bid history from
`/api/loads?status=all&include_missing=true`, excluding orders still open. This
includes expired and declined orders with no bid submission, as well as
accepted, pending, lost, and completed records. Missing bid data is labeled as
not recorded. Click column headings to sort by order, order status, route,
amount, outcome, submission status, or decision time; click again to reverse
the order. Unknown values sort last. More information opens a centered,
read-only dialog with bid and order details. The API returns the latest bid
record per order, rather than every historical submission attempt.

The compact table shows 20 records per page. Sort by and Order selectors sort
the complete history before pagination and reset to the first page. First,
previous, next, and last arrows surround the current page number. Live updates
preserve the selected page, clamping it if the result count shrinks. Submission
details remain available in the information dialog.

Status filtering includes accepted, declined, rejected, expired, pending, lost,
in transit, completed, and unknown outcomes, and can be combined with sorting.
Sort by Date exposes created, last synced, decision, pickup, delivery, and expiry
timestamps, with oldest/newest ordering. The table date column follows the
chosen date field. Created uses `board_created_at`; last synced uses
`last_synced_at`. Received is disabled because the API does not provide a
first-received timestamp. Filter and sort changes reset pagination to page one.

The Order type column labels each record as Fixed rate or Open bid and can be
sorted. Bid / rate shows the offered payout for fixed-rate orders and the
submitted bid amount for open-bid orders. Fixed-rate records do not display a
bid outcome.

Bid Logs subscribes to `/api/loads/ws?order_type=all&status=all`. Snapshots,
updates, and heartbeats automatically refresh the history APIs because bid
amounts and submission results are not included in the order stream. Reads are
serialized, and bursts of messages queue one follow-up refresh. Sorting and
open dialog selection are preserved as results change. Disconnections retain
the previous records and reconnect automatically; failed history reads retry
on the next stream message. Leaving the page closes the socket and cancels
pending requests and retry timers.

Production hosting must serve `index.html` for frontend routes so that direct
links and refreshes work with browser routing.

## Commands

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the development server with hot reload |
| `npm run build` | Check TypeScript and build the production app into `dist/` |
| `npm run typecheck` | Check TypeScript without emitting files |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | Run ESLint |

## Styling

Tailwind CSS runs through the `@tailwindcss/vite` plugin in `vite.config.ts`.
`src/index.css` imports Tailwind and registers daisyUI with light and dark
themes, initially following the system color preference. The header button
switches between light and dark mode and remembers your choice in localStorage.
The saved theme is applied before rendering to avoid a flash on reload.
Light mode uses white and pale
blue surfaces with royal-blue accents; dark mode uses navy surfaces with
bright-blue accents. Theme tokens live in `src/index.css` and use the
[daisyUI custom theme format](https://daisyui.com/docs/themes/).
Use Tailwind utility classes
and daisyUI component classes directly in JSX.

Official setup references: [Tailwind CSS](https://tailwindcss.com/docs/installation/using-vite/)
and [daisyUI](https://daisyui.com/docs/install/vite/).

## Environment and API

`.env` contains local configuration and is ignored by Git. Copy `.env.example`
to `.env` on a new checkout. Set `VITE_API_BASE_URL` to the dispatcher origin
(default `http://127.0.0.1:8000`), without `/api`: endpoint definitions include
that prefix. If unset, requests use the frontend origin. Restart Vite after
changing environment variables. During development, requests use Vite's
same-origin proxy, which forwards API requests to `VITE_API_BASE_URL` (or
`http://127.0.0.1:8000` when unset). Start the dispatcher separately. Production
requests use the configured origin directly; the backend must allow the frontend
origin via CORS or be served behind a same-origin reverse proxy.
`VITE_*` values are exposed to the browser and
must not contain secrets. See [Vite environment variables](https://vite.dev/guide/env-and-mode).

`src/api/` groups each resource's requests, live subscriptions, request types,
and response-type exports in one module:

| Module | Responsibilities |
| --- | --- |
| `orders.ts` | Loads, booking actions, decisions, order stream, and expiration |
| `bids.ts` | Bid records, combined bid history, and live bid-log updates |
| `terminals.ts` | Terminal records and live capacity/status updates |
| `fleet.ts` | Units, capacity, projections, and live fleet updates |
| `shipments.ts` | Confirmed shipments and live tracking |
| `activity.ts` | Activity requests, filters, and live event-log updates |
| `overview.ts` | Dashboard overview |
| `system.ts` | Simulation/system status |
| `health.ts` | Backend health |

`client.ts` contains shared fetch/query helpers. `endpoints.ts` centralizes
routes; `types.ts` mirrors response
fields from the backend Pydantic schemas, including nullable values, decimal
strings, and UTC timestamp strings. Types describe expected data and do not
perform runtime validation.

Every resource uses plain named async functions and a shared `apiFetch` helper.
The helper adds the base URL and JSON content type, preserves custom headers,
and returns the native fetch `Response`. It does not read tokens or add
Authorization headers. Check `response.ok` and parse JSON where you call it:

```ts
import { getLoads, getFleetUnit, bidOnLoad } from './api'
import type { Page, LoadView } from './api'

const response = await getLoads({ order_type: 'open_bid', limit: 50 })
if (!response.ok) throw new Error(`Request failed: ${response.status}`)
const loads: Page<LoadView> = await response.json()

const unitResponse = await getFleetUnit('local-unit-uuid')
// Submit only after an explicit user decision.
const bidResponse = await bidOnLoad('external-order-id', { bid_rate: '2100.25' })
```

List functions accept documented pagination and filters. All HTTP functions
accept standard `RequestInit` options, including `signal` for cancellation.
Booking functions set POST and serialize their typed request bodies as JSON.
HTTP errors return a Response with `ok: false`; network errors reject the
promise. Preserve `sync_pending` in action results and reconcile uncertain
502/504 failures rather than blindly retrying submissions. The backend
validates positive bids and the 2,000-character note limit and chooses the
assigned unit.

`connectTerminalStatus()` opens the terminal-status WebSocket using `ws:` or
`wss:` according to the dispatcher URL. The caller must handle messages as
`TerminalStatusEvent`, replace the complete list on snapshot/update/heartbeat,
reconnect after closure, and close the connection when no longer needed.
No subscription message is required.

External-board routes are backend integrations and are not called by these
frontend modules. Documentation pages (`/docs`, `/redoc`, `/openapi.json`) can
be opened directly on the dispatcher origin.
