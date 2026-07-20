import { readFileSync } from 'node:fs';
import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import DashboardMenu from '../src/lib/DashboardMenu.svelte';
import DashboardFooter from '../src/lib/dashboard/DashboardFooter.svelte';
import DashboardSummary from '../src/lib/dashboard/DashboardSummary.svelte';

const summarySource = readFileSync('src/lib/dashboard/DashboardSummary.svelte', 'utf8');
const appStyles = readFileSync('src/app.css', 'utf8');

function themeBlock(selector: string): string {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = appStyles.match(new RegExp(`${escapedSelector} \\{([\\s\\S]*?)\\n\\}`));
  if (!match) throw new Error(`Missing theme block: ${selector}`);
  return match[1];
}

function tokenValue(block: string, token: string): string {
  const match = block.match(new RegExp(`${token}:\\s*(#[0-9a-fA-F]{3,6})\\s*;`));
  if (!match) throw new Error(`Missing color token: ${token}`);
  return match[1];
}

function relativeLuminance(hex: string): number {
  const value = hex.slice(1);
  const expanded = value.length === 3 ? [...value].map((digit) => digit.repeat(2)).join('') : value;
  const channels = expanded.match(/.{2}/g)?.map((channel) => Number.parseInt(channel, 16) / 255);
  if (!channels || channels.length !== 3) throw new Error(`Invalid color: ${hex}`);
  const [red, green, blue] = channels.map((channel) =>
    channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrastRatio(foreground: string, background: string): number {
  const foregroundLuminance = relativeLuminance(foreground);
  const backgroundLuminance = relativeLuminance(background);
  const lighter = Math.max(foregroundLuminance, backgroundLuminance);
  const darker = Math.min(foregroundLuminance, backgroundLuminance);
  return (lighter + 0.05) / (darker + 0.05);
}

describe('DashboardMenu', () => {
  it('uses disclosure semantics instead of ARIA menu semantics', () => {
    const { body } = render(DashboardMenu);

    expect(body).toContain('aria-expanded="false"');
    expect(body).toContain('aria-controls="dashboard-disclosure"');
    expect(body).not.toContain('aria-haspopup');
  });
});

describe('DashboardSummary', () => {
  it('uses the semantic surface, border, and text theme tokens', () => {
    expect(summarySource).toContain('background: var(--pub-surface-2);');
    expect(summarySource).toContain('border-left: 4px solid var(--pub-border);');
    expect(summarySource.match(/color: var\(--pub-ink\);/g)).toHaveLength(2);
  });

  it('keeps normal text at WCAG AA contrast in light and dark modes', () => {
    const lightTheme = themeBlock(':root');
    const darkTheme = themeBlock(":root[data-theme='dark']");

    expect(
      contrastRatio(tokenValue(lightTheme, '--pub-ink'), tokenValue(lightTheme, '--pub-surface-2')),
    ).toBeGreaterThanOrEqual(4.5);
    expect(
      contrastRatio(tokenValue(darkTheme, '--pub-ink'), tokenValue(darkTheme, '--pub-surface-2')),
    ).toBeGreaterThanOrEqual(4.5);
  });

  it('renders the default resident-facing heading and each paragraph', () => {
    const { body } = render(DashboardSummary, {
      props: { summary: { body: ['First paragraph.', 'Second paragraph.'] } },
    });

    expect(body).toContain('What this means for you');
    expect(body).toContain('First paragraph.');
    expect(body).toContain('Second paragraph.');
    expect(body).toContain('aria-label="What this means"');
  });

  it('renders a custom heading', () => {
    const { body } = render(DashboardSummary, {
      props: { summary: { heading: 'Local context', body: ['Explanation.'] } },
    });
    expect(body).toContain('Local context');
  });
});

describe('DashboardFooter', () => {
  it('renders source, freshness, safe links, caveats, and the report action', () => {
    const { body } = render(DashboardFooter, {
      props: {
        panel: {
          title: 'Roads',
          stats: [],
          charts: [],
          source: 'Road commission',
          lastUpdated: '2026-06',
          links: [{ text: 'Source page', href: 'https://example.gov/roads' }],
          notes: ['Historical data.'],
        },
      },
    });

    expect(body).toContain('Source: Road commission');
    expect(body).toContain('Data as of June 2026');
    expect(body).toContain('href="https://example.gov/roads"');
    expect(body).toContain('Historical data.');
    expect(body).toContain('mailto:explore@burtonmi.gov');
    expect(body).toContain('Report outdated information');
  });
});
