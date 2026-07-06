import { describe, it, expect } from 'vitest';
import { boundaryClipPath } from '../src/lib/map/clip';
import { escapeHtml } from '../src/lib/map/html';

// A unit square boundary inside bounds twice its size: every ring corner lands at
// a 25%/75% intersection, so the percentages are easy to eyeball.
const bounds: [[number, number], [number, number]] = [
  [0, 0],
  [2, 2],
];
const square = [
  [0.5, 0.5],
  [1.5, 0.5],
  [1.5, 1.5],
  [0.5, 1.5],
  [0.5, 0.5],
];

describe('boundaryClipPath', () => {
  it('maps a Polygon ring to element-relative percentages', () => {
    const clip = boundaryClipPath({ type: 'Polygon', coordinates: [square] }, bounds);
    expect(clip).toBe(
      'polygon(25.00% 75.00%, 75.00% 75.00%, 75.00% 25.00%, 25.00% 25.00%, 25.00% 75.00%)',
    );
  });

  it('unwraps a Feature and uses a MultiPolygon’s first exterior ring', () => {
    const feature = {
      type: 'Feature',
      geometry: { type: 'MultiPolygon', coordinates: [[square]] },
    };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect(boundaryClipPath(feature as any, bounds)).toBe(
      boundaryClipPath({ type: 'Polygon', coordinates: [square] }, bounds),
    );
  });

  it('returns an empty string for unsupported geometry', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect(boundaryClipPath({ type: 'Point', coordinates: [0, 0] } as any, bounds)).toBe('');
  });
});

describe('escapeHtml', () => {
  it('escapes all HTML-significant characters', () => {
    expect(escapeHtml(`<img src=x onerror="alert('&')">`)).toBe(
      '&lt;img src=x onerror=&quot;alert(&#39;&amp;&#39;)&quot;&gt;',
    );
  });

  it('escapes ampersands but leaves plain text untouched', () => {
    expect(escapeHtml('Burton Bakery & Deli')).toBe('Burton Bakery &amp; Deli');
    expect(escapeHtml('Kelly Road Park')).toBe('Kelly Road Park');
  });
});
