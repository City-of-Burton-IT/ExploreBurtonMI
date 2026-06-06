// Pure, DOM-free formatting of a feature's configured properties into safe
// render instructions. This is the testable core for the detail panel and the
// home of the URL-scheme validation that fixes Finda's `javascript:` gap.

import type { FeatureProperties } from './types';

export type FieldFormat = 'text' | 'url' | 'email' | 'phone' | 'directions';

export interface PropertyConfig {
  field: string;
  label: string;
  format?: FieldFormat;
}

export type Rendered =
  | { kind: 'text'; label: string; value: string }
  | { kind: 'link'; label: string; href: string; text: string };

/**
 * Return a safe http(s) URL or null. Rejects javascript:, data:, etc.
 * A scheme-less value (e.g. "example.com") is treated as https.
 */
export function safeExternalUrl(raw: string): string | null {
  const s = raw.trim();
  if (!s) return null;
  const withScheme = /^[a-z][a-z0-9+.-]*:/i.test(s) ? s : `https://${s}`;
  let u: URL;
  try {
    u = new URL(withScheme);
  } catch {
    return null;
  }
  return u.protocol === 'http:' || u.protocol === 'https:' ? u.href : null;
}

/**
 * Defense-in-depth href guard for links from data-driven (but trusted) sources
 * like info-*.json and guide.json: permits relative paths and #anchors and the
 * http(s)/mailto/tel schemes, neutralizing any other scheme (javascript:, data:,
 * vbscript:) to "#". Unlike safeExternalUrl this keeps relative/anchor links intact.
 */
export function safeHref(raw: string): string {
  const s = (raw ?? '').trim();
  const scheme = s.match(/^([a-z][a-z0-9+.-]*):/i);
  if (!scheme) return s || '#'; // relative path or #anchor -- safe
  return /^(https?|mailto|tel)$/i.test(scheme[1]) ? s : '#';
}

/** Return a `mailto:` href or null. */
export function safeMailto(raw: string): string | null {
  const s = raw.trim();
  // minimal shape check; we are not validating deliverability
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s)) return null;
  return `mailto:${s}`;
}

/** Return a `tel:` href or null. */
export function safeTel(raw: string): string | null {
  const cleaned = raw.replace(/[^\d+]/g, '');
  if (cleaned.replace(/\D/g, '').length < 7) return null;
  return `tel:${cleaned}`;
}

/** Build a Google Maps directions URL to an address (always safe - we construct it). */
export function directionsUrl(address: string): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(
    address.trim(),
  )}`;
}

function asText(value: unknown): string {
  if (Array.isArray(value)) return value.join(', ');
  return String(value);
}

function isEmpty(value: unknown): boolean {
  return (
    value == null ||
    value === '' ||
    (Array.isArray(value) && value.length === 0)
  );
}

/**
 * Render the configured properties of a feature into safe instructions.
 * Empty values and fields that fail validation (e.g. a bad URL) are dropped.
 */
export function renderProperties(
  props: PropertyConfig[],
  feature: FeatureProperties,
): Rendered[] {
  const out: Rendered[] = [];
  for (const p of props) {
    const value = feature[p.field];
    if (isEmpty(value)) continue;
    const text = asText(value);

    switch (p.format) {
      case 'url': {
        const href = safeExternalUrl(text);
        if (href) out.push({ kind: 'link', label: p.label, href, text: displayHost(href) });
        break;
      }
      case 'email': {
        const href = safeMailto(text);
        if (href) out.push({ kind: 'link', label: p.label, href, text });
        break;
      }
      case 'phone': {
        const href = safeTel(text);
        if (href) out.push({ kind: 'link', label: p.label, href, text });
        break;
      }
      case 'directions': {
        out.push({
          kind: 'link',
          label: p.label,
          href: directionsUrl(text),
          text: 'Get directions',
        });
        break;
      }
      default:
        out.push({ kind: 'text', label: p.label, value: text });
    }
  }
  return out;
}

function displayHost(href: string): string {
  try {
    return new URL(href).host.replace(/^www\./, '');
  } catch {
    return href;
  }
}
