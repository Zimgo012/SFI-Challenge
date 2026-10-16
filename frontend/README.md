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
| Analytics | `/analytics` | Daily estimated profit/loss, bid requests, outcomes, and lane performance with date filters. |
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
Unknown URLs show a page-not-found screen. Pages use backend data;
unavailable figures are not replaced with simulated counts.
Terminal rows expand with View fleet to show their units and schedules from
`/api/fleet/schedules?terminal=CODE`. Each unit expands inline to show confirmed
assignments, occupied windows including turnaround, and provisional reservations.
Lists contain 20 units per page and can include past assignments. Expanded views
refresh on order/terminal snapshots and heartbeats, retain previous data on read
errors, and cancel requests when collapsed. The order stream is shared across
expanded terminals and closes when all rows collapse.

The Terminals page subscribes to `/api/terminals/status/ws` and displays hub
status and local/board capacity. Snapshots, updates,
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

Dashboard combines `/api/overview` totals and profit estimates with full order
and terminal WebSocket snapshots. It shows open opportunities, available trucks,
pending bids, active shipments, and capacity by hub. Preview
lists show up to five records; summary counts use full live data rather than
preview lengths. Active shipments exclude completed bookings. Unknown capacity
stays unknown, and confirmed estimates remain separate from conditional pending
bid profit. Active shipment and pending bid previews show at most five records,
ordered by order creation time, newest first. Terminal capacity uses a full-width
SVG globe with public-domain Natural Earth land outlines, subtle dotted land
texture, and thin country/regional borders. Flat surfaces, compact controls,
and plain labels with small status dots keep the map minimal in both themes.
Status circles stay at their exact geographic coordinates; only nearby labels
are separated in screen space to keep every terminal clickable, with thin
connectors back to their true locations. Labels avoid covering status circles.
Very dense views put additional terminals in a selectable row below the map.
Terminal codes and
markers use API latitude/longitude and the same equirectangular projection
as the SVG. Hover or focus a code to preview live capacity; select it to keep
details and a terminal-schedules link open below the map. The dashboard fills the
available width, with a larger map (460px on mobile, 560px on tablet, 640px on
desktop) automatically fitted to the terminal region. The selected
terminal persists during capacity updates. Labels stay readable as the map resizes
with the sidebar or viewport. Missing/invalid coordinates are listed below the
map. Geography is bundled locally, requires no tile requests, and loads in a
separate bundle. Stream changes
refresh overview metadata, with a 30-second REST fallback and a manual Refresh
button. Connection failures retain previous data; leaving the page closes both
streams, aborts reads, and cancels refresh timers.

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
Cards have labeled View / Accept and Decline buttons. View / Accept opens the profit analyzer
in a right-side panel for both order types, including order details in a tab.
Fixed-rate analysis previews the offered payout,
selected-unit costs, profit margin, and eligibility without editable pricing
controls or a slider. Accept offer inside the panel submits the acceptance only
after an eligible current preview. Open-bid analysis retains its linked margin
and bid inputs; only submitting that form sends a bid.
The analyzer uses a wide panel with margin controls and key profit figures beside
Price analysis, Economics, and Order details tabs. Both open-bid and fixed-rate
cards open Price analysis first. Compact eligibility checks appear below the margin controls. Its submit button stays visible
at the bottom; smaller screens stack the sections above that footer.
The percentage input and slider calculate
the bid from selected-unit total cost, rounded up to cents; a manual bid can
override this target. Read-only cost previews show loaded/deadhead costs, gross
profit, actual margin, minimum profitable bid, and dispatch eligibility. Unknown
costs stay unknown. Changing the bid or receiving a new order snapshot invalidates
the previous preview; submission requires a matching eligible evaluation. Bid
amounts accept up to 16 whole digits and two decimal places. Decline submits the
documented decline action. Expired orders and disconnected streams disable
submissions. Accept opens a sliding right-side dialog with pricing,
costs, assignment, location, and sync information, keyboard focus trapping,
Escape/backdrop dismissal, and reduced-motion support. Countdown
values are labeled as simulated seconds at the last update. Disconnects retain
previous results with a warning and reconnect automatically; leaving the page
closes the connection and cancels timers.

Opening Price analysis for an open bid automatically requests
`POST /api/loads/{external_id}/price-analysis`. Its responsive SVG line chart plots
required bid against profit margin using the backend's estimated cost, with
the price axis fitted to the displayed values and a baseline touching the curve's
starting point. Reference prices below that starting price remain visible, with
horizontal reference lines for cost, minimum profitable bid, model or baseline
advice, and historical baseline. Prices and the current margin appear inside
compact callout boxes connected to their points; nearby callouts are spaced apart
without moving the underlying data. The numeric legend below the plot is removed.
The current bid marker moves immediately as
the slider or bid input changes; backend refreshes are debounced by 500ms. Missing
values stay unavailable rather than becoming zero. Compact bar charts below the
line chart use compact vertical columns with values above and labels below,
arranged side by side when the panel is wide enough: profit and bid/advisory difference in USD, margin and deviation
in percent, and bid/advisory rates in USD per loaded mile. Each group has its own
scale and shows negative values below zero. The duplicate current-bid
readout and analysis options are omitted. Model support, release,
and uncertainty warnings remain visible. HTTP 200 with unavailable advice retains deterministic
economics and shows the backend's error message.

Fixed-rate Price analysis reuses the automatic `/cost-preview` response with no
`bid_rate` in the request. It shows the immutable offered payout on the margin
curve, cost and minimum profitable rate callouts, and vertical bars for cost,
gross profit, margin/configured minimum, and offered/cost rates per loaded mile.
Unavailable costs stay unavailable, and unknown distances never produce a rate.
The same response supplies fixed-rate historical lane context: median and average
payout callouts plus a shaded observed min/max range on the chart. The history
summary shows sample counts, rates per mile, payout standard deviation, simulation
lookback dates, matching method and warnings. Sparse history is marked as limited
data; missing or mismatched history is not replaced with zero or open-bid history.
The chart explicitly labels model advice as unavailable because the backend
rejects fixed-rate analysis with 422. It does not call that endpoint or substitute
historical prices for model advice. Acceptance and its eligibility checks are unchanged.

Analysis uses the current bid and a fresh request UUID; the backend selects the
current eligible unit and resolves the lane from the order's terminal codes.
Changed bid, shipment attributes, or an explicit unit invalidate
results and abort pending reads; unchanged heartbeat metadata preserves them.
While a new bid is being analyzed, the chart keeps the previous references for
the same shipment/unit, explicitly labeled, with the live bid marker. Returned
profit/comparison charts wait for a matching response. Shipment/unit/lane changes
clear those references. Leaving the tab cancels outstanding requests and debounce
timers. Failed requests expose Retry analysis; they are not retried in a loop.
Advice never changes the bid or the existing submission checks.
`getPriceAnalysis` is exported with the other order APIs and returns the native
Response. The browser uses the existing dispatcher proxy; configure the model
URL on the backend as described in the updated API reference.

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

## Analytics

`/analytics` reads all pages of retained orders from `/api/loads?status=all&include_missing=true`
and request events from `/api/activity?event_type=action.requested`. It uses no
sample data and requires no new backend endpoint. Order WebSocket updates trigger
a serialized refresh; a 30-second poll and Refresh button also reload the data.
Failed reads preserve the previous results; leaving the page aborts requests and
cleans up the WebSocket, timers and event listeners. REST history remains the
source because the live order stream omits removed board records.

The default range is 14 UTC days ending on the backend simulation date. Presets
cover 7, 14, 30 and 90 days; custom ranges support 1–366 inclusive days. Select
pickup or delivery day for shipment statistics and optionally filter order type.
The profit/loss chart shows saved confirmed-booking estimates with positive and
negative bars and a net line. Missing estimates are excluded and counted;
pending-bid estimates are separate. These figures are not realized earnings.
Hover/tap a day or focus a chart and use arrow keys, Home or End for its values.

Daily bids count distinct retained `bid requested` action events by simulation
timestamp, including repeated attempts and later failures. They do not use order
creation or scheduled decision time as a submission timestamp. Cleared activity
cannot be reconstructed; events without simulation timestamps are excluded and
reported. New opportunities use order creation day. Current won/lost/pending
outcomes, resolved win rate, order mix, and top five lanes use the selected
shipment-date cohort. Hiding shipment or bid-list history does not remove
retained orders from analytics. Imported historical CSV data is not exposed by
these endpoints and is not included.

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

### Reusable UI components

React, TypeScript, Tailwind CSS v4, and shadcn-compatible configuration are already
installed. `components.json` points reusable primitives to `src/components/ui/`;
`@/` resolves to `src/` in Vite and TypeScript. Keep primitives in this folder so
copied `@/components/ui/...` imports and the shadcn CLI resolve consistently.
App-specific components remain in `src/components/`. Shared `cn()` class merging
lives in `src/lib/utils.ts`; global styles and theme tokens stay in `src/index.css`.
The shadcn color utilities reference the existing daisyUI theme, so the globe,
buttons, and tooltips follow the light/dark toggle.

To add another primitive to this configured project:

```sh
npx shadcn@latest add card
```

For a separate fresh Vite project, the [shadcn CLI](https://ui.shadcn.com/docs/installation/vite)
can scaffold the setup with `npx shadcn@latest init -t vite`.

The supplied globe primitives are in `src/components/ui/globe.tsx`, with its SVG
geography, pulse, and tooltip adapter under `globe-utils/`. The adapter supports
the sample's `render` prop using Radix's `asChild` API. Tooltip content is portaled
outside the SVG to prevent clipping. `src/components/ui/demo.tsx` exports the
standalone sample; the dashboard uses live API terminals through
`src/components/TerminalCapacityMap.tsx` instead of the demo's sample figures.

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

History cleanup requests live with their resources: `deleteOldestActivity`,
`deleteOldestShipments`, and `deleteOldestBids`, also exported from `src/api`.
They accept `{ count, dry_run? }` plus optional `RequestInit`, validate a whole
count from 1 to 10,000, and return the native `Response`. Activity additionally
accepts `external_id` and exact `event_type` filters. `HistoryCleanupResult`
describes selected/deleted/protected counts, record IDs, and deletion mode.

```ts
import { deleteOldestActivity } from './api'
import type { HistoryCleanupResult } from './api'

const response = await deleteOldestActivity({
  count: 100,
  dry_run: true,
  event_type: 'sync.error',
})
if (!response.ok) throw new Error('Unable to preview history cleanup.')
const preview: HistoryCleanupResult = await response.json()
console.log(preview.matched_count, preview.protected_count)
```

Use `dry_run: true` to preview; omitting it performs cleanup. After a real cleanup,
refetch the resource list and overview. Shipment and bid histories respect the
API's durable deletion markers even when retained orders arrive over WebSocket.
Live opportunities remain visible according to order status.

Activity, Bid Logs, and Shipments each provide a Delete oldest records control
with a count input (1–10,000). Submitting deletes the oldest eligible history
across pages, displays actual deleted/protected counts, closes stale details,
returns to page one, and refreshes the list and overview. Activity uses its
applied order/event filters; shipment and bid cleanup use the endpoint's global
eligible scope regardless of table filters. Duplicate requests are blocked while
pending, and uncertain failures refresh the list without retrying deletion.

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
