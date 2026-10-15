/**
 * Generates the static brand kit in public/brand/ (plus public/favicon.svg and
 * the web manifest).
 *
 *   node scripts/build-brand-assets.mjs
 *
 * The full-logo files embed the Geist latin subset as base64 so the wordmark
 * renders correctly anywhere (slides, docs, email), not only on machines that
 * have the font installed. The mark geometry mirrors
 * src/components/brand/Logo.tsx — change both together.
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';

const INK = '#0B0C0F';
const PAPER = '#F3F3F5';
const BLUE_LIGHT = '#0062D1';
const BLUE_DARK = '#5AA9FF';

const font = readFileSync(
  'node_modules/@fontsource-variable/geist/files/geist-latin-wght-normal.woff2',
).toString('base64');

const mark = (ink, blue) => `
  <path d="M16 2.6 27.6 9.3v13.4L16 29.4 4.4 22.7V9.3Z" stroke="${ink}" stroke-width="2.4" stroke-linejoin="round" fill="none"/>
  <g stroke="${ink}" stroke-width="2" stroke-linecap="round" fill="none">
    <path d="M16 16V8.4"/><path d="M16 16 9.4 19.8"/><path d="M16 16l6.6 3.8"/>
  </g>
  <g fill="${ink}"><circle cx="16" cy="8" r="1.9"/><circle cx="9" cy="20" r="1.9"/><circle cx="23" cy="20" r="1.9"/></g>
  <circle cx="16" cy="16" r="3" fill="${blue}"/>`;

const lockup = (ink, blue) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 236 48" width="472" height="96">
  <defs><style>
    @font-face { font-family: 'IB Geist'; font-weight: 100 900; src: url(data:font/woff2;base64,${font}) format('woff2'); }
    text { font-family: 'IB Geist', 'Geist', sans-serif; font-size: 30px; letter-spacing: -1.2px; fill: ${ink}; }
  </style></defs>
  <g transform="translate(4 4) scale(1.25)">${mark(ink, blue)}</g>
  <text x="54" y="34"><tspan font-weight="420">indus</tspan><tspan font-weight="760">brain</tspan></text>
</svg>`;

const files = {
  // Symbol only, transparent — light backgrounds.
  'brand/icon-light.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="64" height="64">${mark(INK, BLUE_LIGHT)}</svg>`,
  // Symbol only, transparent — dark backgrounds.
  'brand/icon-dark.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="64" height="64">${mark(PAPER, BLUE_DARK)}</svg>`,
  // App icon: black tile, light mark. Square; the platform applies its own mask.
  'brand/app-icon.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <rect width="512" height="512" rx="116" fill="${INK}"/>
  <g transform="translate(96 96) scale(10)">${mark(PAPER, BLUE_DARK)}</g>
</svg>`,
  // Favicon: the same tile, scaled down.
  'favicon.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="8" fill="${INK}"/>
  <g transform="translate(4 4) scale(0.75)">${mark(PAPER, BLUE_DARK)}</g>
</svg>`,
  'brand/logo-light.svg': lockup(INK, BLUE_LIGHT),
  'brand/logo-dark.svg': lockup(PAPER, BLUE_DARK),
};

mkdirSync('public/brand', { recursive: true });
for (const [path, svg] of Object.entries(files)) {
  writeFileSync(`public/${path}`, svg.trim() + '\n');
  console.log('wrote public/' + path);
}

writeFileSync(
  'public/manifest.webmanifest',
  JSON.stringify(
    {
      name: 'IndusBrain',
      short_name: 'IndusBrain',
      description: 'Industrial knowledge intelligence: ask your plant documentation.',
      start_url: '/',
      display: 'standalone',
      background_color: INK,
      theme_color: INK,
      icons: [{ src: '/brand/app-icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' }],
    },
    null,
    2,
  ) + '\n',
);
console.log('wrote public/manifest.webmanifest');
