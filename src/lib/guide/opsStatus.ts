// Seasonal City Services Status -- data model + pure helpers behind
// OpsStatus.svelte (the Resident Guide's "City Services Status" section).
// Driven by public/ops-status.json (committed, city-curated). Display-only
// public content (no resident PII).

export type OpsStatusKey = 'in-progress' | 'scheduled' | 'complete' | 'standby';

export interface OpsLink {
  text: string;
  href: string;
}

export interface OpsItem {
  id: string;
  /** the service name, e.g. "Leaf pickup" */
  service: string;
  status: OpsStatusKey;
  /** a short plain-language detail ("Zone 2 this week...") */
  detail: string;
  /** whether the city is running this service now; only active items show */
  active: boolean;
  link?: OpsLink;
}

export interface OpsStatusBundle {
  /** the date the city last edited the file (display only) */
  updated?: string;
  items: OpsItem[];
}

/** Display metadata for a status: a human label, a colour, and an icon key the
 *  component maps to SVG markup. */
export interface OpsStatusMeta {
  label: string;
  color: string;
  icon: OpsStatusKey;
}

const STATUS_META: Record<OpsStatusKey, OpsStatusMeta> = {
  'in-progress': { label: 'In progress', color: '#1d7f2b', icon: 'in-progress' },
  scheduled: { label: 'Scheduled', color: '#2c57a0', icon: 'scheduled' },
  complete: { label: 'Complete', color: '#4b5563', icon: 'complete' },
  standby: { label: 'Standby', color: '#6b7280', icon: 'standby' },
};

/** The services to show now: only those the city has flagged active, in file order. */
export function activeOpsItems(items: OpsItem[]): OpsItem[] {
  return items.filter((i) => i.active);
}

/** Display metadata for a status; falls back to a neutral "standby" look for an
 *  unrecognised value so an unexpected city entry never crashes the panel. */
export function statusMeta(status: string): OpsStatusMeta {
  return STATUS_META[status as OpsStatusKey] ?? { label: status, color: '#6b7280', icon: 'standby' };
}

/**
 * Validate a fetched ops-status.json payload. Fails LOUDLY (throws) on a
 * malformed bundle rather than letting OpsStatus.svelte destructure undefined
 * fields -- mirrors validateData/validateConfig's style.
 */
export function validateOpsStatusBundle(raw: unknown): OpsStatusBundle {
  const errors: string[] = [];
  const b = raw as Partial<OpsStatusBundle>;

  if (!b || typeof b !== 'object') {
    throw new Error('ops-status.json is not an object');
  }

  if (!Array.isArray(b.items)) {
    errors.push('items must be an array');
  } else {
    b.items.forEach((it, i) => {
      const item = it as Partial<OpsItem> | null | undefined;
      if (!item || typeof item !== 'object') {
        errors.push(`items[${i}] is not an object`);
        return;
      }
      if (!item.id) errors.push(`items[${i}].id is required`);
      if (!item.service) errors.push(`items[${i}].service is required`);
      if (!item.status) errors.push(`items[${i}].status is required`);
      if (typeof item.detail !== 'string' || !item.detail) {
        errors.push(`items[${i}].detail is required`);
      }
      if (typeof item.active !== 'boolean') errors.push(`items[${i}].active must be a boolean`);
    });
  }

  if (errors.length) {
    throw new Error(`Invalid ops-status.json:\n - ${errors.join('\n - ')}`);
  }
  return b as OpsStatusBundle;
}
