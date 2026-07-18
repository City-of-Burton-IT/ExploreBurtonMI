// Build the Resident Guide content bundle. Reads content/guide/* (Markdown + the
// contacts/meetings JSON) and emits public/guide.json for the app:
//   { sections: [{id,title,type}], pdf, content: {id: html}, contacts, meetings }
// Markdown is rendered to HTML at build time (devDependency `marked`), so the app
// ships no Markdown parser. hrefs are restricted to safe schemes as a guard.
//
// Run automatically via the npm prebuild/predev scripts, or: node tools/build_guide.mjs

import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import { renderSafeGuideMarkdown } from './guide-html.mjs';
import { writeValidatedGuideBundle } from './guide-output.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'content', 'guide');
const OUT = join(ROOT, 'public', 'guide.json');

/** Read a required content file, turning a missing file into a friendly,
 *  actionable error instead of a raw ENOENT stack trace (this runs as
 *  npm predev/prebuild, so a missing file would otherwise block all local dev). */
function readContentFile(path, description) {
  try {
    return readFileSync(path, 'utf8');
  } catch (err) {
    if (err.code === 'ENOENT') {
      throw new Error(
        `Missing ${description}: ${path}\n` +
        `Check content/guide/index.json -- the referenced file may be missing, ` +
        `misspelled, or not yet created.`,
      );
    }
    throw err;
  }
}

const index = JSON.parse(readContentFile(join(SRC, 'index.json'), 'guide index'));
const out = { sections: [], pdf: index.pdf, content: {} };

for (const s of index.sections) {
  const meta = { id: s.id, title: s.title, type: s.type };
  if (s.icon) meta.icon = s.icon;
  // A video section carries its embed details in the section meta (no body).
  if (s.type === 'video') {
    meta.src = s.src;
    if (s.provider) meta.provider = s.provider;
    if (s.poster) meta.poster = s.poster;
  }
  out.sections.push(meta);

  const file = s.file ? join(SRC, s.file) : null;
  if (s.type === 'markdown') {
    out.content[s.id] = renderSafeGuideMarkdown(
      readContentFile(file, `markdown source for section '${s.id}'`),
      s.id,
    );
  } else if (s.type === 'contacts') {
    out.contacts = JSON.parse(readContentFile(file, `contacts source for section '${s.id}'`));
  } else if (s.type === 'meetings') {
    out.meetings = JSON.parse(readContentFile(file, `meetings source for section '${s.id}'`));
  } else if (
    s.type === 'waste' ||
    s.type === 'ops-status' ||
    s.type === 'civicclerk' ||
    s.type === 'video'
  ) {
    // Rendered by a component from live/static data or section meta; no body to ship.
  } else {
    throw new Error(`Unknown section type '${s.type}' for '${s.id}'`);
  }
}

await writeValidatedGuideBundle(out, OUT, async (bundle) => {
  const vite = await createServer({
    root: ROOT,
    configFile: false,
    appType: 'custom',
    logLevel: 'silent',
    server: { middlewareMode: true },
  });
  try {
    const { validateGuideBundle } = await vite.ssrLoadModule('/src/lib/guide/guideBundle.ts');
    validateGuideBundle(bundle);
  } finally {
    await vite.close();
  }
});
console.log(`Wrote ${OUT} (${index.sections.length} sections)`);
