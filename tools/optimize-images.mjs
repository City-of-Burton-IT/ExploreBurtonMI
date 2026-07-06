// Re-encode oversized public/ content images in place (same filename + format,
// so nothing that references them needs to change). Re-run after replacing
// any of the source images below:
//   node tools/optimize-images.mjs
//
// PWA icons (pwa-192/512/maskable-512.png, apple-touch-icon.png) are NOT
// handled here -- they're generated from public/burton-seal.png by
// tools/gen-pwa-icons.mjs, which already writes optimized output. Re-run that
// script instead of hand-editing its output.

import sharp from 'sharp';
import { statSync, renameSync, unlinkSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const pub = (f) => join(ROOT, 'public', f);

// maxDim = longest-edge cap in px, based on real display usage (see the
// review notes in this file's PR / task). null/omitted maxDim means "already
// sized correctly for its usage -- only re-encode, don't resize".
const TARGETS = [
  {
    // Guide markdown image (content/guide/trash-recycling.md), viewed inline
    // (max-width: 100% of the content column) and full-size in the lightbox
    // (up to 96vw x 82vh). 1008x1101 is a sensible lightbox size already --
    // only the encoding was wasteful.
    file: 'emterra-recycling.png',
    format: 'png',
  },
  {
    // Panel header logo (src/lib/InfoView.svelte), rendered at height: 56px
    // only -- never shown larger or in a lightbox. 3000x3000 is ~50x more
    // resolution than needed even at 3x DPI; cap at 512 (2x a generous
    // ~256px display ceiling, and the floor this task calls for).
    file: 'cityofburton_firedeptlogo_nobackground.png',
    format: 'png',
    maxDim: 512,
  },
  {
    // Source image for tools/gen-pwa-icons.mjs (up to 512px output) and
    // tools/gen-app-assets.mjs (Capacitor splash screens need up to ~900px).
    // Also shown directly at width: 44px (src/lib/App.svelte /
    // ComingSoon.svelte / privacy.html). Keep the current 945x837 so the
    // Capacitor splash generator (out of scope here) doesn't upscale more
    // than it already mildly does -- only re-encode.
    file: 'burton-seal.png',
    format: 'png',
  },
  {
    // Guide markdown image (content/guide/welcome.md), same inline/lightbox
    // usage as emterra-recycling.png above. 1152x1334 is reasonable for a
    // full-screen lightbox view -- only re-encode.
    file: 'burton-historical-plat-map.jpg',
    format: 'jpeg',
  },
];

async function optimize({ file, format, maxDim }) {
  const path = pub(file);
  const before = statSync(path).size;
  const img = sharp(path);
  const meta = await img.metadata();

  let pipeline = sharp(path);
  if (maxDim && Math.max(meta.width, meta.height) > maxDim) {
    pipeline = pipeline.resize({
      width: meta.width >= meta.height ? maxDim : undefined,
      height: meta.height > meta.width ? maxDim : undefined,
      fit: 'inside',
      withoutEnlargement: true,
    });
  }

  if (format === 'png') {
    pipeline = pipeline.png({ palette: true, quality: 80, compressionLevel: 9 });
  } else {
    pipeline = pipeline.jpeg({ quality: 78, mozjpeg: true });
  }

  const tmp = `${path}.tmp`;
  await pipeline.toFile(tmp);
  const after = statSync(tmp).size;
  const outMeta = await sharp(tmp).metadata();

  if (after >= before) {
    unlinkSync(tmp);
    console.log(
      `SKIP ${file}: re-encode (${after}B) was not smaller than original (${before}B); left untouched.`
    );
    return { file, before, after: before, width: meta.width, height: meta.height, skipped: true };
  }

  renameSync(tmp, path);
  console.log(
    `${file}: ${before}B (${meta.width}x${meta.height}) -> ${after}B (${outMeta.width}x${outMeta.height}) ` +
      `[-${(((before - after) / before) * 100).toFixed(1)}%]${outMeta.hasAlpha ? ' alpha' : ''}`
  );
  return { file, before, after, width: outMeta.width, height: outMeta.height, skipped: false };
}

const results = [];
for (const t of TARGETS) {
  results.push(await optimize(t));
}

const totalBefore = results.reduce((s, r) => s + r.before, 0);
const totalAfter = results.reduce((s, r) => s + r.after, 0);
console.log(
  `\nTotal: ${totalBefore}B -> ${totalAfter}B (saved ${totalBefore - totalAfter}B, ` +
    `${(((totalBefore - totalAfter) / totalBefore) * 100).toFixed(1)}%)`
);
