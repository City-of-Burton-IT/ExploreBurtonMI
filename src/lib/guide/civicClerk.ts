export interface CivicClerkEvent {
  id: number;
  eventName: string;
  startDateTime: string;
  categoryName?: string;
  agendaId?: number;
  mediaStreamPath?: string;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function optionalString(value: unknown): string | undefined | null {
  if (value === undefined || value === null) return undefined;
  if (typeof value !== 'string') return null;
  return value.trim() || undefined;
}

function optionalPositiveInteger(value: unknown): number | undefined | null {
  if (value === undefined || value === null || value === 0) return undefined;
  return Number.isInteger(value) && Number(value) > 0 ? Number(value) : null;
}

export function validateCivicClerkEvents(raw: unknown, label: string): CivicClerkEvent[] {
  if (!isObject(raw) || !Array.isArray(raw.value)) {
    throw new Error(`${label} CivicClerk response value must be an array`);
  }
  const errors: string[] = [];
  const ids = new Set<number>();
  const events: CivicClerkEvent[] = [];
  raw.value.forEach((event, index) => {
    const path = `${label}.value[${index}]`;
    if (!isObject(event)) {
      errors.push(`${path} is not an object`);
      return;
    }
    const id = event.id;
    const eventName = typeof event.eventName === 'string' ? event.eventName.trim() : '';
    const startDateTime = event.startDateTime;
    const categoryName = optionalString(event.categoryName);
    const agendaId = optionalPositiveInteger(event.agendaId);
    const mediaStreamPath = optionalString(event.mediaStreamPath);
    if (!Number.isInteger(id) || Number(id) <= 0) errors.push(`${path}.id must be a positive integer`);
    else if (ids.has(Number(id))) errors.push(`${path}.id is duplicated`);
    else ids.add(Number(id));
    if (!eventName) errors.push(`${path}.eventName is required`);
    if (typeof startDateTime !== 'string' || Number.isNaN(Date.parse(startDateTime))) {
      errors.push(`${path}.startDateTime must be a valid date-time`);
    }
    if (categoryName === null) errors.push(`${path}.categoryName must be a non-empty string`);
    if (agendaId === null) errors.push(`${path}.agendaId must be a positive integer`);
    if (mediaStreamPath === null) errors.push(`${path}.mediaStreamPath must be a non-empty string`);
    if (
      Number.isInteger(id) &&
      Number(id) > 0 &&
      eventName &&
      typeof startDateTime === 'string' &&
      !Number.isNaN(Date.parse(startDateTime)) &&
      categoryName !== null &&
      agendaId !== null &&
      mediaStreamPath !== null
    ) {
      events.push({
        id: Number(id),
        eventName,
        startDateTime,
        ...(categoryName ? { categoryName } : {}),
        ...(agendaId ? { agendaId } : {}),
        ...(mediaStreamPath ? { mediaStreamPath } : {}),
      });
    }
  });
  if (errors.length) throw new Error(`Invalid CivicClerk response:\n - ${errors.join('\n - ')}`);
  return events;
}
