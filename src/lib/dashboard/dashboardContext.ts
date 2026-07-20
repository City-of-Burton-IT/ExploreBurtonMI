import type { DashboardStatus } from '../types';

const STATUS_LABELS: Record<DashboardStatus, string> = {
  current: 'Latest available data',
  historical: 'Historical record',
  modeled: 'Model-based estimate',
  planned: 'Adopted plan',
  reference: 'Reference information',
};

export function dashboardStatusLabel(status: DashboardStatus): string {
  return STATUS_LABELS[status];
}
