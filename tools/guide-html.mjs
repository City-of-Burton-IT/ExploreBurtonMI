import { marked } from 'marked';
import { renderGuideMarkdown } from './guide-callouts.mjs';

const SAFE_TAGS = new Set([
  'a',
  'blockquote',
  'br',
  'circle',
  'code',
  'del',
  'div',
  'em',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'hr',
  'img',
  'li',
  'ol',
  'p',
  'path',
  'pre',
  'rect',
  'strong',
  'svg',
  'table',
  'tbody',
  'td',
  'th',
  'thead',
  'tr',
  'ul',
]);
const SAFE_ATTRIBUTES = new Set([
  'align',
  'alt',
  'aria-hidden',
  'class',
  'cx',
  'cy',
  'd',
  'fill',
  'height',
  'href',
  'r',
  'role',
  'rx',
  'ry',
  'src',
  'stroke',
  'stroke-linecap',
  'stroke-linejoin',
  'stroke-width',
  'title',
  'viewbox',
  'width',
  'x',
  'y',
]);
const CALLOUT_TYPES = new Set(['contact', 'important', 'key-date', 'tip']);

function decodeHtmlEntities(value) {
  return value
    .replace(/&#x([0-9a-f]+);?/gi, (_match, hex) => String.fromCodePoint(parseInt(hex, 16)))
    .replace(/&#([0-9]+);?/g, (_match, decimal) => String.fromCodePoint(parseInt(decimal, 10)))
    .replace(/&(colon|tab|newline|sol|bsol|amp);/gi, (_match, name) => {
      const entities = { colon: ':', tab: '\t', newline: '\n', sol: '/', bsol: '\\', amp: '&' };
      return entities[name.toLowerCase()];
    });
}

function normalizedDestination(value) {
  let decoded = String(value).trim();
  for (let i = 0; i < 4; i += 1) {
    const entitiesDecoded = decodeHtmlEntities(decoded);
    let percentDecoded;
    try {
      percentDecoded = decodeURIComponent(entitiesDecoded);
    } catch {
      return null;
    }
    if (percentDecoded === decoded) break;
    decoded = percentDecoded;
  }
  return decoded.replace(/[\u0000-\u0020\u007f]+/g, '').replace(/\\/g, '/');
}

function isSafeLink(value) {
  const destination = normalizedDestination(value);
  if (!destination || destination.startsWith('//')) return false;
  if (destination.startsWith('#')) return /^#[a-z0-9][a-z0-9_-]*$/i.test(destination);
  if (/^(?:mailto:|tel:)/i.test(destination)) return true;
  if (!/^https?:\/\//i.test(destination)) return false;
  try {
    const url = new URL(destination);
    return (url.protocol === 'http:' || url.protocol === 'https:') && !url.username && !url.password;
  } catch {
    return false;
  }
}

function isSafeImage(value) {
  const destination = normalizedDestination(value);
  return !!destination && /^\/[a-z0-9][a-z0-9/_-]*\.(?:avif|gif|jpe?g|png|webp)$/i.test(destination);
}

function trustError(sectionId, message) {
  return new Error(`Guide section '${sectionId}' ${message}`);
}

function validateCallouts(markdown, sectionId) {
  let open = null;
  let hasBody = false;
  for (const [index, line] of markdown.split(/\r?\n/).entries()) {
    const trimmed = line.trim();
    if (trimmed === ':::') {
      if (!open) throw trustError(sectionId, `has a stray callout closer on line ${index + 1}`);
      if (!hasBody) throw trustError(sectionId, `has an empty '${open}' callout`);
      open = null;
      hasBody = false;
      continue;
    }
    const opener = /^:::([a-z][a-z-]*)$/i.exec(trimmed);
    if (opener) {
      const type = opener[1].toLowerCase();
      if (!CALLOUT_TYPES.has(type)) throw trustError(sectionId, `has an unknown '${type}' callout`);
      if (open) throw trustError(sectionId, `nests a '${type}' callout inside '${open}'`);
      open = type;
      hasBody = false;
      continue;
    }
    if (open && trimmed) hasBody = true;
  }
  if (open) throw trustError(sectionId, `has an unclosed '${open}' callout`);
}

/** Reject authored HTML and unsafe Markdown destinations before rendering. */
export function validateGuideMarkdown(markdown, sectionId) {
  if (typeof markdown !== 'string') throw trustError(sectionId, 'must be a Markdown string');
  if (markdown.includes('<')) {
    throw trustError(sectionId, 'contains raw HTML, which is prohibited');
  }
  validateCallouts(markdown, sectionId);

  const tokens = marked.lexer(markdown);
  marked.walkTokens(tokens, (token) => {
    if (token.type === 'html') {
      throw trustError(sectionId, 'contains raw HTML, which is prohibited');
    }
    if (token.type === 'link' && !isSafeLink(token.href)) {
      throw trustError(sectionId, `contains an unsafe link destination: ${token.href}`);
    }
    if (token.type === 'image' && !isSafeImage(token.href)) {
      throw trustError(sectionId, `contains an unsafe image destination: ${token.href}`);
    }
    if (token.type === 'image' && !String(token.text ?? '').trim()) {
      throw trustError(sectionId, `contains an image without alternative text: ${token.href}`);
    }
  });
}

function attributeValues(html, attribute) {
  const pattern = new RegExp(
    `\\b${attribute}\\s*=\\s*(?:"([^"]*)"|'([^']*)'|([^\\s>]+))`,
    'gi',
  );
  return [...html.matchAll(pattern)].map((match) => match[1] ?? match[2] ?? match[3] ?? '');
}

/** Verify renderer output against the exact tag/attribute and URL policy. */
export function assertGeneratedGuideHtml(html, sectionId) {
  if (typeof html !== 'string') throw trustError(sectionId, 'generated prohibited non-string HTML');
  if (/<!--|<![A-Z]/i.test(html)) {
    throw trustError(sectionId, 'generated prohibited HTML declarations or comments');
  }

  for (const match of html.matchAll(/<\/?\s*([a-z][a-z0-9-]*)\b[^>]*>/gi)) {
    const tag = match[1].toLowerCase();
    if (!SAFE_TAGS.has(tag)) throw trustError(sectionId, `generated prohibited <${tag}> HTML`);
    if (match[0].startsWith('</')) continue;
    for (const attribute of match[0].matchAll(/\s([a-z_:][a-z0-9:.-]*)\s*=/gi)) {
      const name = attribute[1].toLowerCase();
      if (!SAFE_ATTRIBUTES.has(name)) {
        throw trustError(sectionId, `generated prohibited '${name}' HTML attribute`);
      }
    }
  }

  for (const href of attributeValues(html, 'href')) {
    if (!isSafeLink(href)) throw trustError(sectionId, `generated prohibited href: ${href}`);
  }
  for (const src of attributeValues(html, 'src')) {
    if (!isSafeImage(src)) throw trustError(sectionId, `generated prohibited src: ${src}`);
  }
}

/** Render trusted guide Markdown. Authored HTML is never accepted. */
export function renderSafeGuideMarkdown(markdown, sectionId) {
  validateGuideMarkdown(markdown, sectionId);
  const html = renderGuideMarkdown(markdown, (fragment) => marked.parse(fragment));
  assertGeneratedGuideHtml(html, sectionId);
  return html;
}
