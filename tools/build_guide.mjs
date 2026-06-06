// Build the Resident Guide content bundle. Reads content/guide/* (Markdown + the
// contacts/meetings JSON) and emits public/guide.json for the app:
//   { sections: [{id,title,type}], pdf, content: {id: html}, contacts, meetings }
// Markdown is rendered to HTML at build time (devDependency `marked`), so the app
// ships no Markdown parser. hrefs are restricted to safe schemes as a guard.
//
// Run automatically via the npm prebuild/predev scripts, or: node tools/build_guide.mjs

import { readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { marked } from 'marked';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'content', 'guide');
const OUT = join(ROOT, 'public', 'guide.json');

const SAFE_HREF = /^(https?:\/\/|mailto:|tel:|#)/i;

/** Neutralize any link whose scheme isn't http(s)/mailto/tel/anchor. */
function sanitize(html) {
  return html.replace(/href="([^"]*)"/gi, (m, url) =>
    SAFE_HREF.test(url.trim()) ? m : 'href="#"',
  );
}

const index = JSON.parse(readFileSync(join(SRC, 'index.json'), 'utf8'));
const out = { sections: [], pdf: index.pdf, content: {} };

for (const s of index.sections) {
  out.sections.push({ id: s.id, title: s.title, type: s.type });
  const file = s.file ? join(SRC, s.file) : null;
  if (s.type === 'markdown') {
    out.content[s.id] = sanitize(marked.parse(readFileSync(file, 'utf8')));
  } else if (s.type === 'contacts') {
    out.contacts = JSON.parse(readFileSync(file, 'utf8'));
  } else if (s.type === 'meetings') {
    out.meetings = JSON.parse(readFileSync(file, 'utf8'));
  } else if (s.type === 'waste') {
    // Rendered by a component that fetches public/waste-schedule.json at runtime;
    // only the section meta needs to ship in the bundle.
  } else {
    throw new Error(`Unknown section type '${s.type}' for '${s.id}'`);
  }
}

writeFileSync(OUT, JSON.stringify(out, null, 2) + '\n', 'utf8');
console.log(`Wrote ${OUT} (${index.sections.length} sections)`);
