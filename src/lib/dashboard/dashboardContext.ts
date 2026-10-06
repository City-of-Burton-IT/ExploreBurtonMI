import type { DashboardStatus } from '../types';

const STATUS_LABELS: Record<DashboardStatus, string> = {
  current: 'Latest available data',
  historical: 'Historical record',
  modeled: 'Model-based estimate',
  planned: 'Adopted plan',
  reference: 'Reference information',
};

/** Every valid DashboardStatus, derived from the label map so the list exists once. */
export const DASHBOARD_STATUSES: readonly DashboardStatus[] = Object.keys(
  STATUS_LABELS,
) as DashboardStatus[];

export function isDashboardStatus(value: string): value is DashboardStatus {
  return (DASHBOARD_STATUSES as readonly string[]).includes(value);
}

export function dashboardStatusLabel(status: DashboardStatus): string {
  return STATUS_LABELS[status];
}
