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
});
