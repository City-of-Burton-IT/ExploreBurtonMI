// Generate Capacitor source assets (assets/) from the city seal, then run:
//   node tools/gen-app-assets.mjs && npx capacitor-assets generate --android
// @capacitor/assets turns these into the Android adaptive icons + splash screens.

import sharp from 'sharp';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdirSync } from 'node:fs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'public', 'burton-seal.png');
const DIR = join(ROOT, 'assets');
mkdirSync(DIR, { recursive: true });
const out = (f) => join(DIR, f);
const TRANSPARENT = { r: 0, g: 0, b: 0, alpha: 0 };
const WHITE = { r: 255, g: 255, b: 255, alpha: 1 };
const DARK = { r: 11, g: 31, b: 46, alpha: 1 }; // --dim navy

async function sealOn(size, inner, bg, file) {
  const seal = await sharp(SRC)
    .resize(inner, inner, { fit: 'contain', background: TRANSPARENT })
    .png()
    .toBuffer();
  await sharp({ create: { width: size, height: size, channels: 4, background: bg } })
    .composite([{ input: seal, gravity: 'center' }])
    .png()
    .toFile(out(file));
}

// Adaptive icon: foreground = seal in the central safe zone (transparent), background = white.
await sharp(SRC)
  .resize(620, 620, { fit: 'contain', background: TRANSPARENT })
  .extend({ top: 202, bottom: 202, left: 202, right: 202, background: TRANSPARENT }) // -> 1024, seal ~60%
  .png()
  .toFile(out('icon-foreground.png'));
await sharp({ create: { width: 1024, height: 1024, channels: 4, background: WHITE } })
  .png()
  .toFile(out('icon-background.png'));
// Legacy/full icon + splash screens.
await sealOn(1024, 760, WHITE, 'icon-only.png');
await sealOn(2732, 900, WHITE, 'splash.png');
await sealOn(2732, 900, DARK, 'splash-dark.png');
console.log('Capacitor source assets written to assets/');
