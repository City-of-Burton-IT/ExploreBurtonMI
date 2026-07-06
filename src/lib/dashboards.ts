// Pure dashboard registry + hash-routing helpers -- no runes, no reactive state,
// safe to import from anywhere (including tests) without pulling in Svelte.

import type { AppView, InfoView } from './types';

export interface DashboardItem {
  id: InfoView;
  label: string;
  /** optional one-line plain-language description: a sub-line in the menu and a
   *  subtitle fallback on the panel. Interim wording -- resident-tested copy is
   *  finalized (with city approval) in issue #38. */
  description?: string;
}
export interface DashboardGroup {
  label: string;
  items: DashboardItem[];
}

/** Dashboards organized into themed groups -- the single source of truth for the
 *  grouped menu, hash routing, and which panels to load. Add a dashboard by
 *  placing it in the right group; everything else derives from this. */
export const DASHBOARD_GROUPS: DashboardGroup[] = [
  {
    label: 'People & Housing',
    items: [
      { id: 'demographics', label: 'Demographics', description: 'Population, age, and household trends from the U.S. Census.' },
      { id: 'jobs', label: 'Jobs & Employers', description: 'Where residents work, top employers, and commuting.' },
      { id: 'access', label: 'Affordability & Access', description: 'Cost of living, income, and transportation access.' },
      { id: 'housing', label: 'Housing & Growth', description: 'Homes, ownership, values, and how housing has grown.' },
      { id: 'zoning', label: 'Zoning', description: 'How land across the city is zoned and used.' },
      { id: 'schools', label: 'Schools', description: 'Public school districts serving Burton and outcomes.' },
    ],
  },
  {
    label: 'Money & Taxes',
    items: [
      { id: 'finances', label: 'City Finances', description: 'How the city raises and spends money each year.' },
      { id: 'propertytax', label: 'Property Taxes', description: 'What makes up your property tax bill and where it goes.' },
      { id: 'fiscalhealth', label: 'Financial Health', description: "The city's debt, pensions, and long-term outlook." },
      { id: 'capital', label: 'Capital Projects', description: 'Big one-time investments the city has funded: roads, equipment, and facilities.' },
    ],
  },
  {
    label: 'Health & Environment',
    items: [
      { id: 'health', label: 'Community Health', description: 'Health indicators and how Burton compares.' },
      { id: 'water', label: 'Drinking Water', description: 'Your water source, quality, and safety record.' },
      { id: 'environment', label: 'Environment', description: 'Air quality and environmental measures.' },
      { id: 'parks', label: 'Parks', description: 'City and county parks, acreage, and upkeep.' },
      { id: 'trails', label: 'Trails & Pathways', description: 'Walking and biking trails across the city.' },
      { id: 'seniorcenter', label: 'Senior Center', description: 'Programs, activity, and services for seniors.' },
    ],
  },
  {
    label: 'Infrastructure',
    items: [
      { id: 'broadband', label: 'Broadband Access', description: 'Internet providers, speeds, and coverage.' },
      { id: 'bridges', label: 'Bridges & Infrastructure', description: 'Condition and traffic of every bridge in the city.' },
      { id: 'roads', label: 'Roads & Pavement', description: 'Pavement condition of the federal-aid road network.' },
    ],
  },
  {
    label: 'Public Safety',
    items: [
      { id: 'publicsafety', label: 'Burton Fire & Rescue', description: 'Fire & Rescue calls, response, and trends.' },
      { id: 'roadsafety', label: 'Roadway Safety', description: 'Where and how often traffic crashes happen (historical).' },
    ],
  },
];

/** Flat list (display order) derived from the groups -- used by hash routing,
 *  panel loading, and the active-dashboard lookup. */
export const DASHBOARDS: DashboardItem[] = DASHBOARD_GROUPS.flatMap((g) => g.items);

const DASHBOARD_IDS = new Set<string>(DASHBOARDS.map((d) => d.id));

/** True when a view is one of the dashboard info-panels. */
export function isDashboard(view: AppView): view is InfoView {
  return DASHBOARD_IDS.has(view);
}

/** The themed-group label containing a dashboard (e.g. "Money & Taxes"), or null. */
export function dashboardGroupLabel(id: AppView): string | null {
  for (const g of DASHBOARD_GROUPS) if (g.items.some((d) => d.id === id)) return g.label;
  return null;
}

/** The dashboards before/after a given one in the flat display order (for prev/next). */
export function adjacentDashboards(id: AppView): {
  prev: DashboardItem | null;
  next: DashboardItem | null;
} {
  const i = DASHBOARDS.findIndex((d) => d.id === id);
  if (i < 0) return { prev: null, next: null };
  return { prev: DASHBOARDS[i - 1] ?? null, next: DASHBOARDS[i + 1] ?? null };
}

/** Map a URL hash (#finances, #guide, #guide/trash, #opendata, #status?t=..) to a
 *  top-level view. Splits on both `/` and `?` so a query suffix (e.g. the #status
 *  token) never hides the route key. */
export function viewFromHash(hash: string): AppView {
  const key = hash.replace(/^#/, '').split(/[/?]/)[0];
  if (key === 'guide' || key === 'opendata' || key === 'status' || DASHBOARD_IDS.has(key))
    return key as AppView;
  return 'map';
}

/** The guide section id from a `#guide/<id>` hash, or null. */
export function guideSectionFromHash(hash: string): string | null {
  const parts = hash.replace(/^#/, '').split('/');
  return parts[0] === 'guide' && parts[1] ? parts[1] : null;
}
