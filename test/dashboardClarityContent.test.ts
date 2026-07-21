import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { DASHBOARDS } from '../src/lib/dashboards';
import {
  enrichInfoPanel,
  validateDashboardClarityMap,
} from '../src/lib/dashboard/dashboardClarity';
import { validateInfoPanel } from '../src/lib/dashboard/infoPanel';

const ids = DASHBOARDS.map(({ id }) => id);

function loadJson(path: string): unknown {
  return JSON.parse(readFileSync(path, 'utf-8'));
}

function enrichedPanels() {
  const clarity = validateDashboardClarityMap(loadJson('public/dashboard-clarity.json'), ids);
  const freshness = loadJson('public/freshness.json') as Record<string, string>;
  return Object.fromEntries(
    ids.map((id) => {
      const raw = loadJson(`public/info-${id}.json`);
      const panel = enrichInfoPanel(raw, clarity[id], freshness[id]);
      return [id, validateInfoPanel(panel, id)];
    }),
  );
}

describe('committed dashboard clarity content', () => {
  it('enriches and validates all 21 registered dashboards', () => {
    const panels = enrichedPanels();
    expect(Object.keys(panels).sort()).toEqual([...ids].sort());
    for (const panel of Object.values(panels)) {
      expect(panel.headline).toBeTruthy();
      expect(panel.context).toBeTruthy();
      expect(panel.responsibility).toBeTruthy();
      expect(panel.action).toBeTruthy();
      const priorityCount = panel.stats.filter((stat) => stat.priority).length;
      expect(priorityCount).toBeGreaterThan(0);
      expect(priorityCount).toBeLessThanOrEqual(4);
      expect(panel.charts.every((chart) => Boolean(chart.takeaway))).toBe(true);
    }
  });

  it('does not repeat unsupported promises in resident-facing copy', () => {
    const copy = Object.values(enrichedPanels())
      .map((panel) => [
        panel.title,
        panel.subtitle,
        panel.headline,
        panel.summary?.body.join(' '),
        panel.responsibility,
        panel.action?.text,
      ].join(' '))
      .join('\n');

    const banned = [
      /where Burton residents work/i,
      /top employers/i,
      /how quickly/i,
      /most calls are medical/i,
      /building permits/i,
      /tap water is safe/i,
      /how each district is doing/i,
    ];
    for (const phrase of banned) expect(copy).not.toMatch(phrase);
  });

  it('puts corrected scope and time boundaries in the primary context', () => {
    const panels = enrichedPanels();
    expect(panels.jobs.title).toBe('Genesee County Jobs & Industries');
    expect(panels.jobs.context?.scope).toBe('Genesee County');
    expect(panels.schools.title).toBe('School Districts Serving Burton');
    expect(panels.schools.context?.scope).toBe('Districts serving Burton');
    expect(panels.roads.context?.scope).toBe('Federal-aid roads in Burton');
    expect(panels.roadsafety.context?.status).toBe('historical');
    expect(panels.roadsafety.context?.asOf).toContain('2014–2018');
    expect(panels.finances.context?.asOf).toContain('FY2026–27 plan');
    expect(panels.finances.context?.asOf).toContain('FY2025 audited');
  });

  it('protects the highest-risk corrected explanations', () => {
    const panels = enrichedPanels();
    expect(panels.access.summary?.body[0]).toMatch(/rounded.*may not sum/i);
    expect(panels.housing.summary?.body[0]).toMatch(/nominal|not adjusted for inflation/i);
    expect(panels.water.summary?.body[0]).toMatch(/system-level|household tap/i);
    expect(panels.publicsafety.summary?.body[0]).toMatch(/758.*responses/i);
    expect(panels.fiscalhealth.summary?.body[0]).toMatch(/not personal bills/i);
    expect(panels.trails.summary?.body[0]).toMatch(/planned.*not open/i);
  });

  it('keeps corrected source-data relationships visible in committed output', () => {
    const trails = loadJson('public/info-trails.json') as {
      tables: Array<{ rows: Array<{ cells: string[] }> }>;
    };
    const trailRows = trails.tables[0].rows;
    expect(trailRows.filter((row) => row.cells[0] === 'Davison Road Trail').map((row) => row.cells[1]))
      .toEqual(['Existing', 'Programmed']);
    expect(trailRows.filter((row) => row.cells[0] === 'Genesee Road Sidewalk').map((row) => row.cells[1]))
      .toEqual(['Under Construction', 'Existing']);

    const senior = loadJson('public/info-seniorcenter.json') as {
      charts: Array<{ title: string; series: Array<{ value: number }> }>;
    };
    const programChart = senior.charts.find((chart) => chart.title === 'Program sign-ins by category');
    expect(programChart?.series.reduce((sum, item) => sum + item.value, 0)).toBe(28_707);

    const fiscal = loadJson('public/info-fiscalhealth.json') as {
      source: string;
      stats: Array<{ label: string; value: string }>;
    };
    expect(fiscal.source).toContain('29,715');
    expect(fiscal.stats.find((stat) => stat.label === 'Long-term debt per resident')?.value).toBe('$985');
    expect(fiscal.stats.find((stat) => stat.label === 'Unfunded pension liability per resident')?.value)
      .toBe('$723');

    const propertyTax = loadJson('public/info-propertytax.json') as {
      estimator: {
        cityRatePeriod: string;
        fullBillRatePeriod: string;
        cityMills: number;
        cityLevies: Array<{
          id: string;
          authorization: string;
          mills: number;
          voterApproved: boolean;
        }>;
      };
      stats: Array<{ label: string; value: string; hint: string }>;
      links: Array<{ text: string; href: string }>;
    };
    expect(propertyTax.estimator.cityMills).toBe(13.2948);
    expect(propertyTax.estimator.cityRatePeriod).toBe('FY2026-27 adopted levy');
    expect(propertyTax.estimator.fullBillRatePeriod).toBe('2025 published rates');
    expect(propertyTax.estimator.cityLevies.map((levy) => levy.mills)).toEqual([
      4,
      8.3159,
      0.9789,
    ]);
    expect(propertyTax.estimator.cityLevies.filter((levy) => levy.voterApproved))
      .toHaveLength(2);
    expect(propertyTax.stats.find((stat) => stat.label === "City of Burton's rate")?.value)
      .toBe('13.2948 mills');
    expect(propertyTax.stats.find((stat) => stat.label === 'Voter-approved City millages')?.value)
      .toBe('9.2948 mills');
    expect(propertyTax.links).toEqual(expect.arrayContaining([
      {
        text: 'City of Burton 2026-27 Approved Budget',
        href: 'https://www.burtonmi.gov/government/controller_s_office/budgets.php',
      },
      {
        text: 'Genesee County L-4029 information',
        href: 'https://www.geneseecountymi.gov/departments/equalization/l-4029_information.php',
      },
      {
        text: 'Michigan property-tax estimator',
        href: 'https://www.michigan.gov/taxes/property/estimator',
      },
    ]));
  });

  it('keeps Property Taxes source periods and authorization plain to residents', () => {
    const propertyTaxPanel = enrichedPanels().propertytax;
    const propertyTax = loadJson('public/info-propertytax.json') as {
      estimator: { cityLevies: Array<{ authorization: string }> };
    };

    expect(propertyTaxPanel.context).toEqual(expect.objectContaining({
      asOf: 'FY2026-27 City levy; 2025 complete-bill rates',
      sourceLinks: [
        {
          text: '2026-27 Approved Budget',
          href: 'https://www.burtonmi.gov/government/controller_s_office/budgets.php',
        },
        {
          text: 'Genesee County L-4029 information',
          href: 'https://www.geneseecountymi.gov/departments/equalization/l-4029_information.php',
        },
        {
          text: 'Michigan property-tax estimator',
          href: 'https://www.michigan.gov/taxes/property/estimator',
        },
      ],
    }));
    expect(propertyTaxPanel.headline).toContain('13.2948 mills');
    expect(propertyTaxPanel.headline).toContain('9.2948 voter-approved');
    expect(propertyTaxPanel.headline).toContain('4.0000 charter');
    expect(JSON.stringify(propertyTaxPanel)).toContain('FY2026-27');
    expect(JSON.stringify(propertyTaxPanel)).toContain('2025');
    expect(JSON.stringify(propertyTaxPanel)).not.toContain('13.44-mill City rate is about 29%');
    expect(JSON.stringify(propertyTaxPanel)).not.toContain('components round to 13.43');
    expect(propertyTax.estimator.cityLevies.map((levy) => levy.authorization)).toEqual([
      'City Charter',
      'Voter approved',
      'Voter approved',
    ]);
  });

  it('uses verified resident-service destinations for high-value actions', () => {
    const panels = enrichedPanels();
    expect(panels.zoning.action).toEqual({
      kind: 'link',
      text: 'Contact the Burton Zoning Division',
      href: 'https://www.burtonmi.gov/departments/department_of_public_works/zoning_division.php',
    });
    expect(panels.water.action).toEqual({
      kind: 'link',
      text: "Read Burton's 2025 water quality report",
      href: 'https://www.burtonmi.gov/departments/department_of_public_works/water_testing.php',
    });
    expect(panels.environment.action?.href).toBe(
      'https://www.airnow.gov/?city=Burton&state=MI&country=USA',
    );
    expect(panels.seniorcenter.action?.href).toBe(
      'https://www.burtonmi.gov/departments/senior_activity_center/index.php',
    );
    expect(panels.roads.action).toEqual({
      kind: 'link',
      text: 'Report a road issue to Burton',
      href: 'https://www.burtonmi.gov/citizen_request_center/index.php',
    });

    expect(panels.propertytax.action?.href).toBe('#propertytax');
    expect(panels.parks.action?.href).toBe('#map');
    expect(panels.trails.action?.href).toBe('#map');
    expect(panels.publicsafety.action).toEqual({
      kind: 'none',
      text: 'Call 911 for an emergency.',
    });
  });
});
