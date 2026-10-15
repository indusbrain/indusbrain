# IndusBrain frontend — working notes

## Stack

This is a **Vite + React 19 + Tailwind CSS v4** single-page application.

**It is not a Next.js app.** An earlier version was scaffolded with Next.js, and
this file used to instruct readers to consult `node_modules/next/dist/docs/`.
That guidance was stale and actively misleading: `next` is not in
`package.json`, so that path does not exist. The leftover `src/app/`,
`next.config.ts` and `next-env.d.ts` files were dead code and have been removed.
There is no App Router and no server components.

- Routing: `react-router-dom` v7, browser history
- Styling: Tailwind v4 via `@tailwindcss/vite`; **all design tokens in `src/styles/tokens.css`**
  (both themes), base styles + motion keyframes in `src/index.css`. Design language and
  brand kit: `BRAND.md`.
- Motion: `motion` (Framer Motion) for staggered reveals and route transitions —
  shared helpers in `src/components/motion/`.
- Theme: `data-theme` on `<html>` (`src/lib/theme.tsx`), set pre-paint by `index.html`.
- Markdown: `markdown-to-jsx` for assistant answers
- No component library — shared primitives live in `src/components/ui/`

## Layout

```
src/
  App.tsx                    routes + dashboard polling
  lib/
    api.ts                   the ONLY API client; injects the role header
    types.ts                 mirrors backend response contracts
    RoleContext.tsx          role state; permissions fetched from the server
  components/
    AppShell.tsx             sidebar, nav, role switcher, service health
    EvidencePanel.tsx        citations / confidence / history / decision replay
    ErrorBoundary.tsx        stops one bad component blanking the app
    brand/                   Logo, LogoMark, Wordmark (+ logo.css motion)
    motion/                  Reveal, CountUp, RouteTransition, IntroSequence
    viz/                     Gauge (instrument dial)
    ui/Backdrop.tsx          wallpaper + noise + cursor-focus grid
    RequirePermission.tsx    route guard with an explained refusal
    ui/                      primitives + icons
  pages/                     one file per route
```

## Conventions

- **Never invent data for display.** If the API returns nothing, render an empty
  state that says *why* it is empty. The backend deliberately returns
  `empty_reason` fields for this purpose.
- **Types mirror the API.** Update `src/lib/types.ts` when a backend contract
  changes, so a mismatch fails at compile time instead of blanking a page at
  runtime. A removed field once crashed the chat panel via `.map()` on
  `undefined`.
- **Monospace is for data only** — asset tags, filenames, measurements, work
  orders. Prose is always sans-serif.
- **Permissions come from the server.** Never hardcode a role's permission list
  in the UI; call `can(permission)` from `useRole()`. The API is the authority
  and returns 403 regardless of what the UI renders.
- **Respect `prefers-reduced-motion`.** All animations are disabled under it, and
  severity is never conveyed by motion alone.
- **Boxes are only for main containers** (`Card` / `.glass`). Labels, statuses and
  tags are coloured text — `Badge` renders plain text on purpose. Don't add
  bordered or tinted chips around small text.
- **No hard-coded colours, radii or easing.** Use the tokens (`var(--color-*)`,
  `var(--radius-*)`, `var(--ease-*)`) so both themes stay correct.
- **Animation is an enhancement, never the source of a value.** A number must be
  correct even if no animation frame ever runs (hidden tab, reduced motion).

## Commands

```bash
npm run dev      # dev server on :5173
npm run build    # typecheck + production build
npm run lint
```

The backend must be running on `http://localhost:8000`, or set `VITE_API_URL`.
