import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import {
  assertGeneratedGuideHtml,
  renderSafeGuideMarkdown,
  validateGuideMarkdown,
} from '../tools/guide-html.mjs';

describe('guide Markdown trust boundary', () => {
  it('renders the current guide Markdown and renderer-owned callouts', () => {
    const markdown = readFileSync('content/guide/welcome.md', 'utf8');
    const html = renderSafeGuideMarkdown(markdown, 'welcome');
    expect(html).toContain('<h2>Welcome to the City of Burton</h2>');
    expect(html).toContain('callout callout--tip');
    expect(html).toContain('<img src="/burton-historical-plat-map.jpg"');
  });

  it('renders every current Markdown section under the fail-closed policy', () => {
    const index = JSON.parse(readFileSync('content/guide/index.json', 'utf8')) as {
      sections: { id: string; type: string; file?: string }[];
    };
    const markdownSections = index.sections.filter((section) => section.type === 'markdown');
    expect(markdownSections.length).toBeGreaterThan(10);
    for (const section of markdownSections) {
      const markdown = readFileSync(`content/guide/${section.file}`, 'utf8');
      expect(() => renderSafeGuideMarkdown(markdown, section.id)).not.toThrow();
    }
  });

  it.each([
    '<script>alert(1)</script>',
    '<iframe src="https://evil.example"></iframe>',
    '<object data="https://evil.example"></object>',
    '<img src="/ok.png" onerror="alert(1)">',
    '<p style="display:none">hidden</p>',
    '<div data-secret="x">hidden</div>',
    '<img src="/ok.png" onerror="alert(1)"',
  ])('rejects authored raw or malformed HTML: %s', (markdown) => {
    expect(() => validateGuideMarkdown(markdown, 'fixture')).toThrow(/fixture.*raw HTML/i);
  });

  it.each([
    '[unsafe](javascript:alert(1))',
    '[unsafe](data:text/html,%3Cscript%3Ealert(1)%3C/script%3E)',
    '[unsafe](jav&#x61;script:alert(1))',
    '[unsafe](java%73cript:alert(1))',
    '[unsafe](//evil.example/path)',
    '[unsafe](vbscript:msgbox(1))',
    '[unsafe](file:///etc/passwd)',
    '[unsafe](https://user:secret@evil.example/path)',
    '[unsafe](java&#58;script:alert(1))',
  ])('rejects unsafe link destinations: %s', (markdown) => {
    expect(() => renderSafeGuideMarkdown(markdown, 'fixture')).toThrow(
      /fixture.*unsafe link destination/i,
    );
  });

  it.each([
    '![unsafe](javascript:alert(1))',
    '![unsafe](data:text/html,bad)',
    '![unsafe](//evil.example/image.png)',
    '![unsafe](/../private.png)',
    '![unsafe](/%2e%2e/private.png)',
    '![unsafe](https://evil.example/image.png)',
    '![unsafe](/image.svg)',
  ])('rejects unsafe image destinations: %s', (markdown) => {
    expect(() => renderSafeGuideMarkdown(markdown, 'fixture')).toThrow(
      /fixture.*unsafe image destination/i,
    );
  });

  it('allows only the link and image forms used by the guide', () => {
    const markdown = [
      '[Web](https://www.burtonmi.gov)',
      '[Phone](tel:+18107431500)',
      '[Email](mailto:clerk@burtonmi.gov)',
      '[Section](#city-offices)',
      '![Volunteers](/welcomevolunteer.png)',
    ].join('\n\n');
    const html = renderSafeGuideMarkdown(markdown, 'fixture');
    expect(html).toContain(
      '<a target="_blank" rel="noopener noreferrer" href="https://www.burtonmi.gov">Web</a>',
    );
    expect(html).toContain('<a href="#guide/fixture/city-offices">Section</a>');
  });

  it('rejects an image without alternative text', () => {
    expect(() => renderSafeGuideMarkdown('![](/welcomevolunteer.png)', 'fixture')).toThrow(
      /without alternative text/i,
    );
  });

  it.each([
    ':::mystery\nBody\n:::',
    ':::\n',
    ':::tip\n:::',
    ':::tip\nBody',
    ':::tip\n:::contact\nNested\n:::\n:::',
  ])('rejects malformed callout structure: %s', (markdown) => {
    expect(() => renderSafeGuideMarkdown(markdown, 'fixture')).toThrow(/callout/i);
  });

  it.each([
    '<script>alert(1)</script>',
    '<p onclick="alert(1)">bad</p>',
    '<p style="display:none">bad</p>',
    '<p data-secret="x">bad</p>',
    '<a href="javascript:alert(1)">bad</a>',
    '<img src="//evil.example/x.png" alt="bad">',
  ])('fails closed if prohibited HTML reaches the generated-output boundary: %s', (html) => {
    expect(() => assertGeneratedGuideHtml(html, 'fixture')).toThrow(/fixture.*prohibited/i);
  });

  it('rejects external renderer output without safe target and rel attributes', () => {
    expect(() =>
      assertGeneratedGuideHtml('<a href="https://www.burtonmi.gov">City site</a>', 'fixture'),
    ).toThrow(/external link without safe target and rel/i);
  });
});
