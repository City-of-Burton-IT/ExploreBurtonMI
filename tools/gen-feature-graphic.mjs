// Generate the Google Play "feature graphic" (1024x500) for Explore Burton.
// Re-run if the seal or branding changes:
//   node tools/gen-feature-graphic.mjs
// Output: C:/utils/explore-burton-feature-graphic.png (upload to the Play listing).
import sharp from 'sharp';
import { existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
// Transparent seal from the burton-design system (looks clean on the gradient --
// no white box). Falls back to the bundled white-background seal if absent.
const SEAL_TRANSPARENT = 'C:/IT/burton-design/assets/logos/burton-seal-transparent.png';
const SEAL = existsSync(SEAL_TRANSPARENT) ? SEAL_TRANSPARENT : join(ROOT, 'public', 'burton-seal.png');
const OUT = 'C:/utils/explore-burton-feature-graphic.png';

const W = 1024;
const H = 500;
const SEAL_SIZE = 360;
const SEAL_X = 70;
const SEAL_Y = Math.round((H - SEAL_SIZE) / 2);

// Civic palette (matches the app theme + burton-design).
const BLUE = '#2c57a0';
const BLUE_DEEP = '#1f3f78';
const GREEN = '#3c8a5b';

// Background + text as one SVG (Arial resolves on Windows; generic sans-serif fallback).
const bg = Buffer.from(`
<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="${BLUE}"/>
      <stop offset="1" stop-color="${BLUE_DEEP}"/>
    </linearGradient>
  </defs>
  <rect width="${W}" height="${H}" fill="url(#g)"/>
  <rect x="0" y="${H - 14}" width="${W}" height="14" fill="${GREEN}"/>
  <g font-family="Arial, Helvetica, sans-serif">
    <text x="455" y="210" font-size="62" font-weight="700" fill="#ffffff">Explore Burton</text>
    <text x="457" y="268" font-size="32" font-style="italic" fill="#dbe6f4">at the heart of it all</text>
    <text x="457" y="335" font-size="26" fill="#aebfd9">City of Burton, Michigan</text>
    <text x="457" y="377" font-size="22" fill="#9db0d2">Map &#183; Dashboards &#183; Resident Guide</text>
  </g>
</svg>`);

const seal = await sharp(SEAL)
  .resize(SEAL_SIZE, SEAL_SIZE, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
  .png()
  .toBuffer();

await sharp(bg)
  .composite([{ input: seal, left: SEAL_X, top: SEAL_Y }])
  .png()
  .toFile(OUT);

console.log(`Wrote ${OUT} (${W}x${H})`);
