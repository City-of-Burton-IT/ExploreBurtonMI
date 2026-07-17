import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import DashboardMenu from '../src/lib/DashboardMenu.svelte';
import DashboardFooter from '../src/lib/dashboard/DashboardFooter.svelte';
import DashboardSummary from '../src/lib/dashboard/DashboardSummary.svelte';

describe('DashboardMenu', () => {
  it('uses disclosure semantics instead of ARIA menu semantics', () => {
    const { body } = render(DashboardMenu);

    expect(body).toContain('aria-expanded="false"');
    expect(body).toContain('aria-controls="dashboard-disclosure"');
    expect(body).not.toContain('aria-haspopup');
  });
});

describe('DashboardSummary', () => {
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
