import { describe, it, expect } from 'vitest';
import { marked } from 'marked';
import { renderGuideMarkdown } from '../tools/guide-callouts.mjs';

const parse = (s: string) => marked.parse(s) as string;

describe('renderGuideMarkdown (guide callouts)', () => {
  it('converts a :::tip block into a callout box and renders its markdown', () => {
    const html = renderGuideMarkdown(':::tip\nHello **world**\n:::', parse);
    expect(html).toContain('callout callout--tip');
    expect(html).toContain('callout-title');
    expect(html).toContain('Tip');
    expect(html).toContain('<strong>world</strong>');
    expect(html).not.toContain(':::');
  });

  it('supports all four callout types with their titles', () => {
    const cases: [string, string][] = [
      ['important', 'Important'],
      ['key-date', 'Key date'],
      ['contact', 'Contact'],
      ['tip', 'Tip'],
    ];
    for (const [type, title] of cases) {
      const html = renderGuideMarkdown(`:::${type}\nBody\n:::`, parse);
      expect(html).toContain(`callout--${type}`);
      expect(html).toContain(title);
    }
  });

  it('leaves normal markdown (and blockquotes) unchanged', () => {
    const html = renderGuideMarkdown('## Title\n\nA paragraph.\n\n> a quote', parse);
    expect(html).toContain('<h2>Title</h2>');
    expect(html).toContain('<p>A paragraph.</p>');
    expect(html).toContain('<blockquote>');
    expect(html).not.toContain('callout');
  });

  it('leaves an unknown callout type untouched', () => {
    const html = renderGuideMarkdown(':::mystery\nBody\n:::', parse);
    expect(html).not.toContain('callout--mystery');
    expect(html).toContain(':::mystery');
  });

  it('handles two callouts in one document', () => {
    const html = renderGuideMarkdown(':::tip\nOne\n:::\n\n:::important\nTwo\n:::', parse);
    expect(html).toContain('callout--tip');
    expect(html).toContain('callout--important');
    expect((html.match(/class="callout /g) ?? []).length).toBe(2);
  });
});
