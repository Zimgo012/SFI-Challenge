# SFI Challenge frontend

React with TypeScript, Vite, Tailwind CSS, and daisyUI.

## Getting started

```sh
npm install
npm run dev
```

Open the local URL printed by Vite. `/` redirects to `/dashboard`.

## Pages and navigation

| Page | Route |
| --- | --- |
| Dashboard | `/dashboard` |
| Load Board | `/loads` |
| Bidding | `/bids` |
| Terminals | `/terminals` |
| Fleet & Schedule | `/fleet` |
| Shipments | `/shipments` |
| Activity | `/activity` |

Page components live in `src/pages/`. `src/layouts/AppLayout.tsx` provides
shared navigation with active states; `src/config/navigation.ts` defines its
labels and links. `src/App.tsx` declares the routes using
[React Router](https://reactrouter.com/start/declarative/routing).
Unknown URLs show a page-not-found screen. Page content is a scaffold awaiting
backend data; dashboard values are unavailable rather than simulated counts.

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
themes, following the system color preference. Use Tailwind utility classes
and daisyUI component classes directly in JSX.

Official setup references: [Tailwind CSS](https://tailwindcss.com/docs/installation/using-vite/)
and [daisyUI](https://daisyui.com/docs/install/vite/).

## Environment and API

`.env` contains the local configuration and is ignored by Git. New checkouts
can copy `.env.example` to `.env`. Set `VITE_API_BASE_URL` to your backend URL;
`http://localhost:3000/api` is a placeholder until the backend is configured.
If unset, requests use `/api` on the frontend origin. Restart Vite after
changing environment variables. Vite exposes `VITE_*` values to the browser,
so these values must not contain secrets.
See [Vite environment variables](https://vite.dev/guide/env-and-mode).

- `src/config/env.ts`: centralized environment configuration.
- `src/api/endpoints.ts`: add confirmed backend route paths here.
- `src/api/client.ts`: shared fetch client with HTTP error handling.
- `src/api/index.ts`: public API exports.

Once backend routes are known, add entries to `endpoints` and use them with
`apiRequest`. The client supports standard fetch options, including headers
and abort signals. JSON request bodies must be serialized explicitly:

```ts
import { apiRequest } from './api'

// Example only: replace this route and payload with your backend contract.
await apiRequest('/your-endpoint', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ name: 'Example' }),
})
```

Responses are parsed as JSON; empty responses return `undefined`. HTTP errors
throw `ApiError` with `status` and `body`. Network errors propagate from fetch.
Response types describe expected data and do not perform runtime validation.
