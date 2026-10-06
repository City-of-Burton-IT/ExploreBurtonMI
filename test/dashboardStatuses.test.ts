import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';
import DashboardSection from '../src/lib/dashboard/DashboardSection.svelte';
import {
  DASHBOARD_STATUSES,
  dashboardStatusLabel,
  isDashboardStatus,
} from '../src/lib/dashboard/dashboardContext';
import { sectionHeadingId } from '../src/lib/dashboard/dashboardClarity';

describe('dashboard status list', () => {
  it('is the single source for the five statuses and labels each of them', () => {
    expect([...DASHBOARD_STATUSES]).toEqual(['current', 'historical', 'modeled', 'planned', 'reference']);
    for (const status of DASHBOARD_STATUSES) {
      expect(dashboardStatusLabel(status)).toBeTruthy();
      expect(isDashboardStatus(status)).toBe(true);
    }
    expect(isDashboardStatus('draft')).toBe(false);
  });
});

describe('DashboardSection ids', () => {
  it('uses the shared heading id for both the h3 id and aria-labelledby', () => {
    const heading = 'What the City levies';
    const { body } = render(DashboardSection, {
      props: { section: { heading, stats: [] }, stats: [], charts: [], tables: [] },
    });
    const id = sectionHeadingId(heading);
    expect(body).toContain(`aria-labelledby="${id}"`);
    expect(body).toMatch(new RegExp(`<h3 id="${id}"[ >]`));
  });
});
