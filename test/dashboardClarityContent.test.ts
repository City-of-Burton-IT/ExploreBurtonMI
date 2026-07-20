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
      stats: Array<{ label: string; value: string; hint: string }>;
    };
    const cityRate = propertyTax.stats.find((stat) => stat.label === "City of Burton's rate");
    expect(cityRate?.value).toBe('13.44 mills');
    expect(cityRate?.hint).toContain('components round to 13.43');
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
