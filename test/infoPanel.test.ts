import { readdirSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { DASHBOARDS } from '../src/lib/dashboards';
import {
  validateFreshnessMap,
  validateInfoPanel,
  validateSummaryMap,
} from '../src/lib/dashboard/infoPanel';

const dashboardIds = DASHBOARDS.map(({ id }) => id);

const completePanel = {
  title: 'Example dashboard',
  subtitle: 'A complete contract fixture',
  logo: '/example.png',
  draft: true,
  draftNote: 'Pending review',
  summary: { heading: 'What this means', body: ['Plain-language summary.'] },
  explainer: {
    title: 'How this works',
    intro: 'Introduction',
    items: [{ term: 'Term', body: 'Definition' }],
    source: 'Example source',
  },
  methodology: { title: 'Methodology', body: 'Measured consistently.' },
  estimator: {
    cityMills: 12.5,
    countyMills: 8.25,
    districts: [{ name: 'Example district', homestead: 32, nonHomestead: 50 }],
  },
  stats: [
    {
      label: 'Residents',
      value: '1,000',
      hint: 'Latest estimate',
      benchmarks: [{ name: 'Michigan', value: '2,000' }],
      spark: [{ x: '2025', y: 1000 }],
    },
  ],
  charts: [
    { type: 'donut', title: 'Share', unit: '%', series: [{ label: 'Yes', value: 60, color: '#123456' }] },
    { type: 'bars', title: 'Count', series: [{ label: 'Total', value: 10 }] },
    {
      type: 'trend',
      title: 'Trend',
      points: [{ x: '2025', y: 10 }],
      markers: [{ x: '2025', label: 'Event' }],
      lines: [{ label: 'Burton', points: [{ x: '2025', y: 10 }], color: '#123456' }],
    },
    {
      type: 'compare',
      title: 'Comparison',
      citiesLede: 'Compared with nearby cities.',
      rows: [
        {
          label: 'Rate',
          unit: '%',
          values: [{ name: 'Burton', value: 10 }],
          cities: [{ name: 'Flint', value: 11 }],
        },
      ],
    },
  ],
  tables: [{ title: 'Details', columns: ['Name'], rows: [{ cells: ['Example'], color: '#123456' }] }],
  lastUpdated: '2026-07-17',
  source: 'Public source',
  links: [{ text: 'Source page', href: 'https://example.gov/data' }],
  notes: ['A caveat.'],
};

describe('validateInfoPanel', () => {
  it('accepts the complete dashboard contract', () => {
    expect(validateInfoPanel(completePanel, 'example')).toEqual(completePanel);
  });

  it('accepts every committed dashboard panel', () => {
    for (const id of dashboardIds) {
      const raw = JSON.parse(readFileSync(`public/info-${id}.json`, 'utf-8'));
      expect(validateInfoPanel(raw, id)).toEqual(raw);
    }
  });

  it('keeps the dashboard registry and committed panel files in one-to-one sync', () => {
    const files = readdirSync('public')
      .filter((name) => /^info-[a-z]+\.json$/.test(name))
      .map((name) => name.slice('info-'.length, -'.json'.length))
      .sort();

    expect(files).toEqual([...dashboardIds].sort());
  });

  it('rejects an unknown chart type with the dashboard id and field path', () => {
    const invalid = { ...completePanel, charts: [{ type: 'pie', title: 'Invalid' }] };
    expect(() => validateInfoPanel(invalid, 'finances')).toThrow(
      /finances.*charts\[0\]\.type.*unknown chart type/i,
    );
  });

  it('rejects malformed nested chart rows with the field path', () => {
    const invalid = {
      ...completePanel,
      charts: [
        {
          type: 'compare',
          title: 'Comparison',
          rows: [{ label: 'Rate', values: [{ name: 'Burton', value: 'ten' }] }],
        },
      ],
    };
    expect(() => validateInfoPanel(invalid, 'health')).toThrow(
      /health.*charts\[0\]\.rows\[0\]\.values\[0\]\.value/i,
    );
  });

  it('rejects table rows whose cells do not match the column count', () => {
    const invalid = {
      ...completePanel,
      tables: [{ title: 'Details', columns: ['Name', 'Value'], rows: [{ cells: ['Only one'] }] }],
    };
    expect(() => validateInfoPanel(invalid, 'roads')).toThrow(
      /roads.*tables\[0\]\.rows\[0\]\.cells.*2 columns/i,
    );
  });

  it('rejects duplicate values used as top-level Svelte keys', () => {
    const duplicate = completePanel.charts[0];
    const invalid = { ...completePanel, charts: [duplicate, { ...duplicate }] };
    expect(() => validateInfoPanel(invalid, 'finances')).toThrow(
      /finances.*charts\[1\]\.title.*duplicate/i,
    );
  });

  it('rejects duplicate values used as nested chart keys', () => {
    const invalid = {
      ...completePanel,
      charts: [
        {
          type: 'compare',
          title: 'Comparison',
          rows: [
            {
              label: 'Rate',
              values: [
                { name: 'Burton', value: 10 },
                { name: 'Burton', value: 11 },
              ],
            },
          ],
        },
      ],
    };
    expect(() => validateInfoPanel(invalid, 'health')).toThrow(
      /health.*charts\[0\]\.rows\[0\]\.values\[1\]\.name.*duplicate/i,
    );
  });
});

describe('dashboard metadata overlays', () => {
  it('accepts the committed summary and freshness maps', () => {
    const summaries = JSON.parse(readFileSync('public/summaries.json', 'utf-8'));
    const freshness = JSON.parse(readFileSync('public/freshness.json', 'utf-8'));

    expect(validateSummaryMap(summaries, dashboardIds)).toEqual(summaries);
    expect(validateFreshnessMap(freshness, dashboardIds)).toEqual(freshness);
  });

  it('rejects a summary key that is not a registered dashboard', () => {
    expect(() =>
      validateSummaryMap({ typo: { body: ['Summary'] } }, dashboardIds),
    ).toThrow(/summaries\.typo.*registered dashboard/i);
  });

  it('rejects an invalid freshness date with its field path', () => {
    expect(() => validateFreshnessMap({ finances: 'July 2026' }, dashboardIds)).toThrow(
      /freshness\.finances.*YYYY-MM/i,
    );
  });
});
