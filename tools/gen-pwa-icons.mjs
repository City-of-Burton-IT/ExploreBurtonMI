// Generate the PWA icon set from the city seal. Re-run if the seal changes:
//   node tools/gen-pwa-icons.mjs
// Produces (in public/): pwa-192.png, pwa-512.png (transparent, "any"),
// pwa-maskable-512.png (seal in the maskable safe zone on white), and
// apple-touch-icon.png (180, seal on white for iOS home-screen).

import sharp from 'sharp';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'public', 'burton-seal.png');
const out = (f) => join(ROOT, 'public', f);
const TRANSPARENT = { r: 0, g: 0, b: 0, alpha: 0 };
const WHITE = { r: 255, g: 255, b: 255, alpha: 1 };

// Palette PNGs (indexed color) compress far smaller than truecolor for flat,
// low-color-count icon art like the seal, with no visible quality loss.
const PNG_OPTS = { palette: true, quality: 80, compressionLevel: 9 };

/** Square icon, seal scaled to fit (aspect kept), transparent background. */
async function standard(size, file) {
  await sharp(SRC)
    .resize(size, size, { fit: 'contain', background: TRANSPARENT })
    .png(PNG_OPTS)
    .toFile(out(file));
}

/** Square icon with the seal centered at `inner` px on a solid background --
 *  used for maskable (seal inside the safe zone) and the iOS touch icon. */
async function padded(size, inner, bg, file) {
  const seal = await sharp(SRC)
    .resize(inner, inner, { fit: 'contain', background: TRANSPARENT })
    .png()
    .toBuffer();
  await sharp({ create: { width: size, height: size, channels: 4, background: bg } })
    .composite([{ input: seal, gravity: 'center' }])
    .png(PNG_OPTS)
    .toFile(out(file));
}

await standard(192, 'pwa-192.png');
await standard(512, 'pwa-512.png');
await padded(512, 360, WHITE, 'pwa-maskable-512.png'); // seal ~70% -> within the 80% maskable safe zone
await padded(180, 150, WHITE, 'apple-touch-icon.png');
console.log('PWA icons written to public/');
