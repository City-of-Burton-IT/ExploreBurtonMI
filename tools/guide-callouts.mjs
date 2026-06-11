// Resident Guide callout transform: convert ::: containers in the guide markdown
// into styled callout boxes. Shared by build_guide.mjs (build) and its vitest test.
//
// Authoring:
//   :::tip            ... :::      (a helpful tip)
//   :::important      ... :::      (something not to miss)
//   :::key-date       ... :::      (a deadline or date)
//   :::contact        ... :::      (who to call / where to go)
//
// Icons are Lucide (https://lucide.dev, ISC/MIT), inlined so there is no runtime
// third-party request. Credited in the About dialog.

const ICONS = {
  tip: '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>',
  important: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  'key-date': '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
  contact: '<path d="M13.832 16.568a1 1 0 0 0 1.213-.303l.355-.465A2 2 0 0 1 17 15h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2A18 18 0 0 1 2 4a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3a2 2 0 0 1-.8 1.6l-.468.351a1 1 0 0 0-.292 1.233 14 14 0 0 0 6.392 6.384"/>',
};

const TITLES = { tip: 'Tip', important: 'Important', 'key-date': 'Key date', contact: 'Contact' };
const TYPES = new Set(Object.keys(ICONS));

function iconSvg(type) {
  return (
    `<svg class="callout-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" ` +
    `stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[type]}</svg>`
  );
}

function calloutBox(callout, parse) {
  const inner = parse(callout.body).trim();
  return (
    `<div class="callout callout--${callout.type}" role="note">` +
    iconSvg(callout.type) +
    `<div class="callout-body"><p class="callout-title">${TITLES[callout.type]}</p>${inner}</div>` +
    `</div>`
  );
}

/**
 * Render guide markdown to HTML, converting ::: callout containers into boxes.
 * `parse` is the markdown->HTML function (e.g. marked.parse). Pure and testable;
 * unknown callout types are left untouched, and markdown without callouts is
 * rendered exactly as `parse` would on its own.
 */
export function renderGuideMarkdown(md, parse) {
  const callouts = [];
  // Stage each ":::type ... :::" block out to a placeholder before parsing, so the
  // fence lines never reach the markdown renderer. The closer is a bare ":::".
  const staged = md.replace(
    /^:::([a-z][a-z-]*)[ \t]*\r?\n([\s\S]*?)\r?\n:::[ \t]*$/gim,
    (whole, type, body) => {
      const t = String(type).toLowerCase();
      if (!TYPES.has(t)) return whole; // unknown type -> leave as authored
      const i = callouts.push({ type: t, body }) - 1;
      return `\n\n<!--CALLOUT:${i}-->\n\n`;
    },
  );

  let html = parse(staged);
  // marked emits the placeholder comment as a raw HTML block; swap each for its box
  // (tolerating an optional <p> wrap).
  html = html.replace(
    /(?:<p>\s*)?<!--CALLOUT:(\d+)-->(?:\s*<\/p>)?/g,
    (_whole, i) => calloutBox(callouts[Number(i)], parse),
  );
  return html;
}
