import { readFileSync } from 'node:fs';
import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import DashboardMenu from '../src/lib/DashboardMenu.svelte';
import DashboardFooter from '../src/lib/dashboard/DashboardFooter.svelte';
import DashboardSummary from '../src/lib/dashboard/DashboardSummary.svelte';
import InfoHeader from '../src/lib/InfoHeader.svelte';
import InfoView from '../src/lib/InfoView.svelte';

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

  it('renders why it matters, City responsibility, and the resident action', () => {
    const { body } = render(DashboardSummary, {
      props: {
        summary: { heading: 'Why this matters', body: ['The finding affects service planning.'] },
        responsibility: 'Burton manages this service directly.',
        action: { kind: 'link', text: 'Read the service plan', href: 'https://example.gov/plan' },
      },
    });

    expect(body).toContain('Why this matters');
    expect(body).toContain('The finding affects service planning.');
    expect(body).toContain('City responsibility');
    expect(body).toContain('Burton manages this service directly.');
    expect(body).toContain('What you can do');
    expect(body).toContain('href="https://example.gov/plan"');
    expect(body).toContain('aria-label="What this means"');
  });

  it('renders an explicit no-action statement without a disabled link', () => {
    const { body } = render(DashboardSummary, {
      props: {
        summary: { body: ['Explanation.'] },
        responsibility: 'Another agency owns this system.',
        action: { kind: 'none', text: 'No direct resident action is needed.' },
      },
    });
    expect(body).toContain('No direct resident action is needed.');
    expect(body).not.toContain('disabled');
  });
});

describe('InfoHeader data context', () => {
  it.each([
    ['current', 'Latest available data'],
    ['historical', 'Historical record'],
    ['modeled', 'Model-based estimate'],
    ['planned', 'Adopted plan'],
    ['reference', 'Reference information'],
  ] as const)('explains %s information as "%s"', (status, expected) => {
    const { body } = render(InfoHeader, {
      props: {
        title: 'Example dashboard',
        context: { scope: 'City of Burton', status, asOf: 'June 2026' },
      },
    });

    expect(body).toContain(expected);
  });
});

describe('InfoView resident hierarchy', () => {
  it('renders context, headline, priority facts, explanation, and grouped evidence in order', () => {
    const { body } = render(InfoView, {
      props: {
        group: 'Money & Taxes',
        panel: {
          title: 'City Finances',
          subtitle: 'The adopted plan and audited results',
          context: {
            scope: 'City of Burton',
            status: 'planned',
            asOf: 'FY2026–27 plan',
            sourceLinks: [
              { text: '2026-27 Approved Budget', href: 'https://example.gov/budget' },
            ],
          },
          headline: 'The adopted plan totals $67.7 million across all City funds.',
          summary: { heading: 'Why this matters', body: ['A budget is a plan, not a final result.'] },
          responsibility: 'City Council adopts the plan; audited reports show actual results later.',
          action: { kind: 'link', text: 'Read the adopted budget', href: 'https://example.gov/budget' },
          stats: [
            { id: 'total-budget', label: 'Total adopted plan', value: '$67.7M', priority: true },
            { id: 'staff', label: 'Full-time staff', value: '102', priority: false },
          ],
          charts: [
            {
              id: 'funds',
              type: 'bars',
              title: 'Adopted plan by fund',
              takeaway: 'The largest displayed fund carries the most planned spending.',
              series: [{ label: 'General Fund', value: 10 }],
            },
          ],
          tables: [],
          sections: [{ heading: 'Adopted plan', stats: ['staff'], charts: ['funds'] }],
        },
      },
    });

    expect(body).toContain('Money &amp; Taxes');
    expect(body).toContain('About this data');
    expect(body).toContain('This covers');
    expect(body).toContain('City of Burton');
    expect(body).toContain('Information type');
    expect(body).toContain('Adopted plan');
    expect(body).toContain('Time period');
    expect(body).toContain('FY2026–27 plan');
    expect(body).toContain('Official sources');
    expect(body).toContain('2026-27 Approved Budget');
    expect(body).toContain('href="https://example.gov/budget"');
    expect(body).toContain('target="_blank"');
    expect(body).toContain('rel="noopener noreferrer"');
    expect(body).not.toContain('<span>Scope</span>');
    expect(body).not.toContain('<span>Status</span>');
    expect(body).not.toContain('<span>As of</span>');
    expect(body.indexOf('The adopted plan totals')).toBeLessThan(body.indexOf('Total adopted plan'));
    expect(body.indexOf('Total adopted plan')).toBeLessThan(body.indexOf('Why this matters'));
    expect(body.indexOf('Why this matters')).toBeLessThan(body.indexOf('Adopted plan</h3>'));
    expect(body).toContain('The largest displayed fund carries the most planned spending.');
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
