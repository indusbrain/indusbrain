# IndusBrain brand kit — "Glass over noise"

A true-black field with live film grain and a grid that sharpens under the
cursor, and translucent frosted-glass panes (macOS / visionOS) floating on it.
Black is the default theme (the OS preference is ignored); a light theme is a
toggle away. The product is dense with data, so the chrome stays calm: one
container material, coloured text for meaning, no decoration.

All values below live in **`src/styles/tokens.css`** (both themes). Change them
there and the whole app follows. Nothing else should hard-code a colour,
radius or curve.

## The rules

1. **Boxes are only for main containers** — a score, a document list, a form.
   Labels, statuses, tags and sub-text are never boxed; they are coloured text.
   `Badge` renders plain text; the colour is the signal.
2. **Colour carries meaning** — red = problem, amber = needs attention,
   green = healthy, blue = interactive / identifier. Never decoration.
3. **One material** — `.glass` for containers, `.btn-glass` for controls.
4. **Type** — Geist for UI, Geist Mono for data only (asset tags, filenames,
   figures). Prose is never monospace.

## Logo

| File | Use |
|---|---|
| `src/components/brand/Logo.tsx` | In-app: `<Logo />`, `<LogoMark />`, `<Wordmark />` (animated, theme-aware) |
| `public/brand/logo-light.svg` / `logo-dark.svg` | Full lockup for light / dark backgrounds (font embedded) |
| `public/brand/icon-light.svg` / `icon-dark.svg` | Symbol only |
| `public/brand/app-icon.svg` | 512px app / home-screen icon (also in `manifest.webmanifest`) |
| `public/favicon.svg` | Browser tab |

Regenerate the static files with `node scripts/build-brand-assets.mjs`.

**The symbol** is a hex nut — the archetypal piece of industrial hardware —
holding three signals converging on one blue core: many documents, one answer.
**The wordmark** is one family in two weights: regular `indus`, heavy `brain`.

**Motion:** on load the nut draws, the branches run in, the nodes land, then
the core lights. On hover the core pulses and the nodes answer in turn.

## Colour

| Token | Light | Dark | Role |
|---|---|---|---|
| `surface-base` / `--wall-base` | `#E6E9EF` | `#0B0C0F` | Wallpaper |
| `--glass-fill` | white @ 56% | `#202128` @ 52% | Container body |
| `ink-primary` | `#17181C` | `#F3F3F5` | Text |
| `ink-muted` | `#5B5F69` | `#A0A2AB` | Secondary text (AA on glass) |
| `accent` | `#0062D1` | `#5AA9FF` | Interaction, identifiers |
| `danger` | `#C22A14` | `#FF8A76` | Contradictions, failures |
| `warning` | `#8F5F00` | `#F2BC52` | Needs attention |
| `success` | `#1B7A43` | `#6BD39A` | Healthy / documented |

Chart fills (`--color-amber`, `--color-pipe`) are brighter than the text-safe
status colours; a bar needs 3:1, text needs 4.5:1.

## Spacing, radius, shadow

- **Spacing:** 4px base (`--space-1` … `--space-5`), fluid above that;
  page gutter `--gutter` = `clamp(16px, 2.4vw, 32px)`.
- **Radius:** `--radius-sheet` 20px (glass containers), `--radius-control`
  10px (buttons, inputs), `--radius-chip` 6px.
- **Shadow:** `--glass-shadow` — a soft drop plus an inset top highlight, the
  "light catching the glass" edge. `--shadow-float` for drawers and dialogs.

## Background

`components/ui/Backdrop.tsx`, mounted once at the app root, fixed behind
everything: a black field, a noise layer that jitters in steps like film grain
(the "live" noise), a faint grid, and a second, brighter copy of the grid
masked to a 190px circle around the cursor. Moving or dragging the pointer
slides the circle, easing after it (~18% of the remaining distance per frame);
one rAF loop that stops when the circle arrives, no React renders. Nothing
drifts or wobbles. Disabled on touch-only devices; under reduced motion the
circle snaps and the grain holds still.

## Motion

| Curve | Value | Use |
|---|---|---|
| `--ease-valve` | `cubic-bezier(0.2, 0.8, 0.2, 1)` | Arrivals: opens fast, settles softly |
| `--ease-pressure` | `cubic-bezier(0.65, 0, 0.35, 1)` | Loops and returns |
| `--ease-snap` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Press feedback |

Only `transform`, `opacity` and `stroke-dashoffset` animate (plus the sidebar
width). Everything is disabled under `prefers-reduced-motion`, and a value
never depends on an animation finishing.

## Screens

- **Start-up:** black, noisy, logo + 0→100% counter on a fixed ~2.4 s
  timeline, once per session. Any key or click skips it.
- **Login:** black and noisy, Employee / Manager tabs. Demo mode enters as the
  chosen role (no password; the API still enforces permissions). Secure mode
  signs in with email + password and rejects a Manager sign-in from an
  Employee account.
- **Errors:** `FaultNotice` is the only error / warning block — calm and
  minimal: neutral glass, a thin red light down the left edge, one icon, a short
  title and muted detail, one soft fade-in. `ErrorNotice` delegates to it; so do
  the connection banner, the error boundary, login failures and the conflicts
  summary. Content is always the real error; severity is never motion alone.
- **Sidebar:** flush with the window edge (no margin). Navy blue (`#0B1F4A`)
  with light text in the light theme, translucent glass in the black theme.
  Inside it `--color-accent` / `--color-danger` resolve to their navy-safe
  variants (`--color-frame-accent` / `--color-frame-danger`) via `[data-sidebar]`.
  Collapses to a 72px icon rail (never fully hidden) with the button or
  Ctrl/Cmd + B, and remembers the choice. No numbering.
