import { readdirSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { DASHBOARDS } from '../src/lib/dashboards';
import {
  validateFreshnessMap,
  validateInfoPanel,
  validateRawInfoPanel,
} from '../src/lib/dashboard/infoPanel';
import {
  enrichInfoPanel,
  validateDashboardClarityMap,
} from '../src/lib/dashboard/dashboardClarity';

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
    cityRatePeriod: 'FY2026-27 adopted levy',
    fullBillRatePeriod: '2025 published rates',
    cityMills: 13.2948,
    cityLevies: [
      {
        id: 'general-operating',
        service: 'General city operations',
        authorization: 'City Charter',
        description: 'Supports general municipal services.',
        mills: 4,
        voterApproved: false,
      },
      {
        id: 'police',
        service: 'Police services',
        authorization: 'Voter approved',
        description: 'Supports Police Department operations.',
        mills: 8.3159,
        voterApproved: true,
      },
      {
        id: 'fire',
        service: 'Fire services',
        authorization: 'Voter approved',
        description: 'Supports Fire Department operations.',
        mills: 0.9789,
        voterApproved: true,
      },
    ],
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

const completeClarity = {
  context: {
    scope: 'City of Burton',
    status: 'planned',
    asOf: 'FY2026–27 adopted plan',
    sourceLinks: [
      { text: '2026-27 Approved Budget', href: 'https://example.gov/budget' },
    ],
  },
  headline: 'The adopted plan directs the largest share of spending to public services.',
  summary: {
    heading: 'Why this matters',
    body: ['The plan shows what the City expects to collect and spend during the fiscal year.'],
  },
  responsibility: 'Burton adopts and manages this plan; audited results later show what occurred.',
  action: {
    kind: 'link',
    text: 'Read the adopted budget',
    href: 'https://example.gov/budget',
  },
  statOverrides: {
    Residents: { priority: true },
  },
  chartOverrides: {
    Share: { takeaway: 'Most of the displayed share is in the leading category.' },
    Count: { takeaway: 'The chart shows ten recorded items.' },
    Trend: { takeaway: 'The displayed measure is unchanged in the one-year example.' },
    Comparison: { takeaway: 'Burton is one point below the comparison city.' },
  },
  tableIds: {
    Details: 'details',
  },
  sections: [
    {
      heading: 'Evidence',
      charts: ['share', 'count', 'trend', 'comparison'],
      tables: ['details'],
    },
  ],
} as const;

describe('validateInfoPanel', () => {
  it('accepts the complete dashboard contract', () => {
    expect(validateRawInfoPanel(completePanel, 'example')).toEqual(completePanel);
  });

  it.each([
    ['negative mills', { mills: -1 }, /cityLevies\[0\]\.mills.*non-negative/i],
    ['invalid voter flag', { voterApproved: 'yes' }, /cityLevies\[0\]\.voterApproved.*boolean/i],
    ['missing authorization', { authorization: '' }, /cityLevies\[0\]\.authorization/i],
  ] as const)('rejects %s in City levy data', (_label, change, expected) => {
    const levy = { ...completePanel.estimator.cityLevies[0], ...change };
    const invalid = {
      ...completePanel,
      estimator: { ...completePanel.estimator, cityLevies: [levy] },
    };
    expect(() => validateRawInfoPanel(invalid, 'propertytax')).toThrow(expected);
  });

  it('rejects duplicate levy ids', () => {
    const levy = completePanel.estimator.cityLevies[0];
    const invalid = {
      ...completePanel,
      estimator: { ...completePanel.estimator, cityLevies: [levy, { ...levy }] },
    };
    expect(() => validateRawInfoPanel(invalid, 'propertytax')).toThrow(
      /cityLevies\[1\]\.id.*duplicate/i,
    );
  });

  it('rejects a City total that does not equal its levy components', () => {
    const invalid = {
      ...completePanel,
      estimator: { ...completePanel.estimator, cityMills: 99 },
    };
    expect(() => validateRawInfoPanel(invalid, 'propertytax')).toThrow(
      /cityMills.*sum of cityLevies/i,
    );
  });

  it('accepts every committed dashboard panel', () => {
    for (const id of dashboardIds) {
      const raw = JSON.parse(readFileSync(`public/info-${id}.json`, 'utf-8'));
      expect(validateRawInfoPanel(raw, id)).toEqual(raw);
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
    expect(() => validateRawInfoPanel(invalid, 'finances')).toThrow(
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
    expect(() => validateRawInfoPanel(invalid, 'health')).toThrow(
      /health.*charts\[0\]\.rows\[0\]\.values\[0\]\.value/i,
    );
  });

  it('rejects table rows whose cells do not match the column count', () => {
    const invalid = {
      ...completePanel,
      tables: [{ title: 'Details', columns: ['Name', 'Value'], rows: [{ cells: ['Only one'] }] }],
    };
    expect(() => validateRawInfoPanel(invalid, 'roads')).toThrow(
      /roads.*tables\[0\]\.rows\[0\]\.cells.*2 columns/i,
    );
  });

  it('rejects duplicate values used as top-level Svelte keys', () => {
    const duplicate = completePanel.charts[0];
    const invalid = { ...completePanel, charts: [duplicate, { ...duplicate }] };
    expect(() => validateRawInfoPanel(invalid, 'finances')).toThrow(
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
    expect(() => validateRawInfoPanel(invalid, 'health')).toThrow(
      /health.*charts\[0\]\.rows\[0\]\.values\[1\]\.name.*duplicate/i,
    );
  });
});

describe('dashboard clarity contract', () => {
  it('gives every committed dashboard one to three curated official sources', () => {
    const raw = JSON.parse(readFileSync('public/dashboard-clarity.json', 'utf-8'));
    const clarity = validateDashboardClarityMap(raw, dashboardIds);

    for (const id of dashboardIds) {
      const links = clarity[id].context.sourceLinks;
      if (!links) throw new Error(`Missing official sources for ${id}`);
      expect(links.length).toBeGreaterThanOrEqual(1);
      expect(links.length).toBeLessThanOrEqual(3);
      expect(new Set(links.map(({ href }) => href)).size).toBe(links.length);
      expect(links.every(({ href }) => href.startsWith('https://'))).toBe(true);
    }

    expect(clarity.finances.context.sourceLinks).toContainEqual({
      text: '2026-27 Approved Budget',
      href: 'https://www.burtonmi.gov/government/controller_s_office/budgets.php',
    });
  });

  it('enriches a raw panel with stable ids before applying display overrides', () => {
    const clarity = {
      ...completeClarity,
      statOverrides: {
        Residents: { priority: true, label: 'People counted' },
      },
      chartOverrides: {
        ...completeClarity.chartOverrides,
        Share: {
          title: 'How the total is divided',
          takeaway: 'Most of the displayed share is in the leading category.',
        },
      },
    };

    const { lastUpdated: _lastUpdated, ...panelWithoutDate } = completePanel;
    const panel = enrichInfoPanel(panelWithoutDate, clarity, '2026-06');

    expect(panel.stats[0]).toMatchObject({ id: 'residents', label: 'People counted', priority: true });
    expect(panel.charts[0]).toMatchObject({
      id: 'share',
      title: 'How the total is divided',
      takeaway: 'Most of the displayed share is in the leading category.',
    });
    expect(panel.lastUpdated).toBe('2026-06');
    expect(validateInfoPanel(panel, 'example')).toEqual(panel);
  });

  it('rejects an unknown dashboard status with its field path', () => {
    const invalid = {
      example: {
        ...completeClarity,
        context: { ...completeClarity.context, status: 'forecast' },
      },
    };

    expect(() => validateDashboardClarityMap(invalid, ['example'])).toThrow(
      /example.*context\.status.*current.*historical.*modeled.*planned.*reference/i,
    );
  });

  it('preserves curated official source links in dashboard context', () => {
    const validated = validateDashboardClarityMap({ example: completeClarity }, ['example']);

    expect(validated.example.context.sourceLinks).toEqual([
      { text: '2026-27 Approved Budget', href: 'https://example.gov/budget' },
    ]);
  });

  it('rejects a dashboard source link without an https destination', () => {
    const invalid = {
      example: {
        ...completeClarity,
        context: {
          ...completeClarity.context,
          sourceLinks: [{ text: 'Unsafe source', href: 'http://example.gov/data' }],
        },
      },
    };

    expect(() => validateDashboardClarityMap(invalid, ['example'])).toThrow(
      /example.*context\.sourceLinks\[0\]\.href.*https/i,
    );
  });

  it('rejects more than three dashboard source links', () => {
    const invalid = {
      example: {
        ...completeClarity,
        context: {
          ...completeClarity.context,
          sourceLinks: ['one', 'two', 'three', 'four'].map((text) => ({
            text,
            href: `https://example.gov/${text}`,
          })),
        },
      },
    };

    expect(() => validateDashboardClarityMap(invalid, ['example'])).toThrow(
      /example.*context\.sourceLinks.*three/i,
    );
  });

  it('rejects duplicate dashboard source URLs', () => {
    const invalid = {
      example: {
        ...completeClarity,
        context: {
          ...completeClarity.context,
          sourceLinks: [
            { text: 'First label', href: 'https://example.gov/data' },
            { text: 'Second label', href: 'https://example.gov/data' },
          ],
        },
      },
    };

    expect(() => validateDashboardClarityMap(invalid, ['example'])).toThrow(
      /example.*context\.sourceLinks\[1\]\.href.*duplicate/i,
    );
  });

  it('rejects more than four priority facts', () => {
    const invalid = {
      example: {
        ...completeClarity,
        statOverrides: Object.fromEntries(
          ['One', 'Two', 'Three', 'Four', 'Five'].map((label) => [label, { priority: true }]),
        ),
      },
    };

    expect(() => validateDashboardClarityMap(invalid, ['example'])).toThrow(
      /example.*statOverrides.*four priority/i,
    );
  });

  it('rejects duplicate section headings', () => {
    const invalid = {
      example: {
        ...completeClarity,
        sections: [completeClarity.sections[0], completeClarity.sections[0]],
      },
    };

    expect(() => validateDashboardClarityMap(invalid, ['example'])).toThrow(
      /example.*sections\[1\]\.heading.*duplicate/i,
    );
  });

  it('rejects section references that do not exist in the raw panel', () => {
    const invalid = {
      ...completeClarity,
      sections: [{ heading: 'Evidence', charts: ['missing-chart'] }],
    };

    expect(() => enrichInfoPanel(completePanel, invalid, '2026-06')).toThrow(
      /charts.*missing-chart.*unknown/i,
    );
  });

  it('rejects a link action without an https or hash destination', () => {
    const invalid = {
      example: {
        ...completeClarity,
        action: { kind: 'link', text: 'Open details', href: 'javascript:alert(1)' },
      },
    };

    expect(() => validateDashboardClarityMap(invalid, ['example'])).toThrow(
      /example.*action\.href.*https.*hash/i,
    );
  });

  it('rejects a raw chart that has no clarity takeaway', () => {
    const { Share: _share, ...withoutShare } = completeClarity.chartOverrides;
    const invalid = { ...completeClarity, chartOverrides: withoutShare };

    expect(() => enrichInfoPanel(completePanel, invalid, '2026-06')).toThrow(
      /chart.*Share.*takeaway/i,
    );
  });
});

describe('dashboard metadata overlays', () => {
  it('accepts the committed freshness map', () => {
    const freshness = JSON.parse(readFileSync('public/freshness.json', 'utf-8'));

    expect(validateFreshnessMap(freshness, dashboardIds)).toEqual(freshness);
  });

  it('rejects an invalid freshness date with its field path', () => {
    expect(() => validateFreshnessMap({ finances: 'July 2026' }, dashboardIds)).toThrow(
      /freshness\.finances.*YYYY-MM/i,
    );
  });
});
