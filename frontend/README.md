# SFI Challenge frontend

React with TypeScript, Vite, Tailwind CSS, and daisyUI.

## Getting started

```sh
npm install
npm run dev
```

Open the local URL printed by Vite. Edit `src/App.tsx` to start building.

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
