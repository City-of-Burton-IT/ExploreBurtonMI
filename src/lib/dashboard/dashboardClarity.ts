import type {
  DashboardAction,
  DashboardClarity,
  DashboardContext,
  DashboardStatus,
  InfoChart,
  InfoPanel,
  InfoSection,
  InfoStat,
  InfoTable,
} from '../types';
import { validateRawInfoPanel } from './infoPanel';

type JsonObject = Record<string, unknown>;

const DASHBOARD_STATUSES: readonly DashboardStatus[] = [
  'current',
  'historical',
  'modeled',
  'planned',
  'reference',
];

function fail(context: string, path: string, expectation: string): never {
  throw new Error(`Invalid ${context} at ${path}: ${expectation}`);
}
function objectValue(value: unknown, context: string, path: string): JsonObject {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    fail(context, path, 'expected an object');
  }
  return value as JsonObject;
}

function stringValue(value: unknown, context: string, path: string): string {
  if (typeof value !== 'string' || value.trim().length === 0) {
    fail(context, path, 'expected a non-empty string');
  }
  return value;
}

function optionalString(value: unknown, context: string, path: string): void {
  if (value !== undefined) stringValue(value, context, path);
}

function stringArray(value: unknown, context: string, path: string): string[] {
  if (value === undefined) return [];
  if (!Array.isArray(value)) fail(context, path, 'expected an array');
  const strings = value.map((item, index) => stringValue(item, context, `${path}[${index}]`));
  const seen = new Set<string>();
  strings.forEach((item, index) => {
    if (seen.has(item)) fail(context, `${path}[${index}]`, `duplicate value "${item}"`);
    seen.add(item);
  });
  return strings;
}

function wordCount(value: string): number {
  return value.trim().split(/\s+/).filter(Boolean).length;
}

function maxWords(value: string, maximum: number, context: string, path: string): void {
  if (wordCount(value) > maximum) fail(context, path, `expected no more than ${maximum} words`);
}

function validateSourceLinks(
  value: unknown,
  context: string,
  path: string,
): NonNullable<DashboardContext['sourceLinks']> {
  if (value === undefined) return [];
  if (!Array.isArray(value)) fail(context, path, 'expected an array');
  if (value.length === 0 || value.length > 3) {
    fail(context, path, 'expected one to three official source links');
  }

  const seen = new Set<string>();
  return value.map((rawLink, index) => {
    const linkPath = `${path}[${index}]`;
    const link = objectValue(rawLink, context, linkPath);
    const text = stringValue(link.text, context, `${linkPath}.text`);
    const href = stringValue(link.href, context, `${linkPath}.href`);
    if (!href.startsWith('https://')) {
      fail(context, `${linkPath}.href`, 'expected an https URL');
    }
    if (seen.has(href)) {
      fail(context, `${linkPath}.href`, `duplicate URL "${href}"`);
    }
    seen.add(href);
    return { text, href };
  });
}

function validateContext(value: unknown, context: string, path: string): DashboardContext {
  const item = objectValue(value, context, path);
  const scope = stringValue(item.scope, context, `${path}.scope`);
  const status = stringValue(item.status, context, `${path}.status`);
  if (!DASHBOARD_STATUSES.includes(status as DashboardStatus)) {
    fail(
      context,
      `${path}.status`,
      `expected one of current, historical, modeled, planned, reference; received "${status}"`,
    );
  }
  const asOf = stringValue(item.asOf, context, `${path}.asOf`);
  const sourceLinks = validateSourceLinks(item.sourceLinks, context, `${path}.sourceLinks`);
  return {
    scope,
    status: status as DashboardStatus,
    asOf,
    ...(sourceLinks.length ? { sourceLinks } : {}),
  };
}

function validateAction(value: unknown, context: string, path: string): DashboardAction {
  const item = objectValue(value, context, path);
  const kind = stringValue(item.kind, context, `${path}.kind`);
  const text = stringValue(item.text, context, `${path}.text`);
  maxWords(text, 25, context, `${path}.text`);
  if (kind === 'none') return { kind, text };
  if (kind !== 'link') fail(context, `${path}.kind`, 'expected "link" or "none"');
  const href = stringValue(item.href, context, `${path}.href`);
  if (!href.startsWith('https://') && !href.startsWith('#')) {
    fail(context, `${path}.href`, 'expected an https URL or hash link');
  }
  return { kind, text, href };
}

function validateSummary(value: unknown, context: string, path: string): DashboardClarity['summary'] {
  const item = objectValue(value, context, path);
  optionalString(item.heading, context, `${path}.heading`);
  if (!Array.isArray(item.body) || item.body.length !== 1) {
    fail(context, `${path}.body`, 'expected exactly one paragraph');
  }
  const paragraph = stringValue(item.body[0], context, `${path}.body[0]`);
  maxWords(paragraph, 80, context, `${path}.body[0]`);
  return {
    ...(item.heading === undefined ? {} : { heading: item.heading as string }),
    body: [paragraph],
  };
}

function validateStatOverrides(
  value: unknown,
  context: string,
  path: string,
): DashboardClarity['statOverrides'] {
  const overrides = objectValue(value, context, path);
  let priorityCount = 0;
  for (const [label, rawOverride] of Object.entries(overrides)) {
    stringValue(label, context, `${path}.${label}`);
    const override = objectValue(rawOverride, context, `${path}.${label}`);
    optionalString(override.label, context, `${path}.${label}.label`);
    optionalString(override.hint, context, `${path}.${label}.hint`);
    if (override.priority !== undefined && typeof override.priority !== 'boolean') {
      fail(context, `${path}.${label}.priority`, 'expected a boolean');
    }
    if (override.priority === true) priorityCount += 1;
  }
  if (priorityCount > 4) fail(context, path, 'expected no more than four priority facts');
  return overrides as DashboardClarity['statOverrides'];
}

function validateChartOverrides(
  value: unknown,
  context: string,
  path: string,
): DashboardClarity['chartOverrides'] {
  const overrides = objectValue(value, context, path);
  for (const [title, rawOverride] of Object.entries(overrides)) {
    stringValue(title, context, `${path}.${title}`);
    const override = objectValue(rawOverride, context, `${path}.${title}`);
    optionalString(override.title, context, `${path}.${title}.title`);
    const takeaway = stringValue(override.takeaway, context, `${path}.${title}.takeaway`);
    maxWords(takeaway, 35, context, `${path}.${title}.takeaway`);
  }
  return overrides as DashboardClarity['chartOverrides'];
}

function validateTableIds(
  value: unknown,
  context: string,
  path: string,
): Record<string, string> {
  const ids = objectValue(value, context, path);
  const seen = new Set<string>();
  for (const [title, rawId] of Object.entries(ids)) {
    stringValue(title, context, `${path}.${title}`);
    const id = stringValue(rawId, context, `${path}.${title}`);
    if (seen.has(id)) fail(context, `${path}.${title}`, `duplicate id "${id}"`);
    seen.add(id);
  }
  return ids as Record<string, string>;
}

function validateSections(value: unknown, context: string, path: string): InfoSection[] {
  if (!Array.isArray(value) || value.length === 0) {
    fail(context, path, 'expected a non-empty array');
  }
  const headings = new Set<string>();
  return value.map((rawSection, index) => {
    const sectionPath = `${path}[${index}]`;
    const section = objectValue(rawSection, context, sectionPath);
    const heading = stringValue(section.heading, context, `${sectionPath}.heading`);
    if (headings.has(heading)) fail(context, `${sectionPath}.heading`, `duplicate value "${heading}"`);
    headings.add(heading);
    const stats = stringArray(section.stats, context, `${sectionPath}.stats`);
    const charts = stringArray(section.charts, context, `${sectionPath}.charts`);
    const tables = stringArray(section.tables, context, `${sectionPath}.tables`);
    if (stats.length + charts.length + tables.length === 0) {
      fail(context, sectionPath, 'expected at least one stat, chart, or table reference');
    }
    return {
      heading,
      ...(stats.length ? { stats } : {}),
      ...(charts.length ? { charts } : {}),
      ...(tables.length ? { tables } : {}),
    };
  });
}

function validateClarity(value: unknown, id: string): DashboardClarity {
  const contextName = `dashboard clarity "${id}"`;
  const item = objectValue(value, contextName, '$');
  optionalString(item.title, contextName, 'title');
  optionalString(item.subtitle, contextName, 'subtitle');
  const context = validateContext(item.context, contextName, 'context');
  const headline = stringValue(item.headline, contextName, 'headline');
  maxWords(headline, 30, contextName, 'headline');
  const summary = validateSummary(item.summary, contextName, 'summary');
  const responsibility = stringValue(item.responsibility, contextName, 'responsibility');
  maxWords(responsibility, 55, contextName, 'responsibility');
  const action = validateAction(item.action, contextName, 'action');
  const statOverrides = validateStatOverrides(item.statOverrides, contextName, 'statOverrides');
  const chartOverrides = validateChartOverrides(item.chartOverrides, contextName, 'chartOverrides');
  const tableIds = validateTableIds(item.tableIds, contextName, 'tableIds');
  const sections = validateSections(item.sections, contextName, 'sections');
  return {
    ...(item.title === undefined ? {} : { title: item.title as string }),
    ...(item.subtitle === undefined ? {} : { subtitle: item.subtitle as string }),
    context,
    headline,
    summary,
    responsibility,
    action,
    statOverrides,
    chartOverrides,
    tableIds,
    sections,
  };
}

export function validateDashboardClarityMap(
  value: unknown,
  dashboardIds: readonly string[],
): Record<string, DashboardClarity> {
  const map = objectValue(value, 'dashboard clarity metadata', '$');
  const knownIds = new Set(dashboardIds);
  for (const id of Object.keys(map)) {
    if (!knownIds.has(id)) fail('dashboard clarity metadata', id, 'expected a registered dashboard id');
  }
  for (const id of dashboardIds) {
    if (!(id in map)) fail('dashboard clarity metadata', id, 'expected a clarity record');
  }
  return Object.fromEntries(dashboardIds.map((id) => [id, validateClarity(map[id], id)]));
}

export function stableDashboardId(value: string): string {
  const id = value
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
  if (!id) throw new Error(`Cannot create a dashboard id from "${value}"`);
  return id;
}

function ensureKnownOverrides(
  overrides: Record<string, unknown>,
  sourceValues: readonly string[],
  kind: string,
): void {
  const known = new Set(sourceValues);
  for (const sourceValue of Object.keys(overrides)) {
    if (!known.has(sourceValue)) {
      throw new Error(`Invalid dashboard clarity ${kind} override "${sourceValue}": unknown source value`);
    }
  }
}

function ensureUniqueIds(items: readonly { id?: string }[], kind: string): void {
  const seen = new Set<string>();
  for (const item of items) {
    if (!item.id) throw new Error(`Invalid dashboard clarity ${kind}: missing id`);
    if (seen.has(item.id)) throw new Error(`Invalid dashboard clarity ${kind}: duplicate id "${item.id}"`);
    seen.add(item.id);
  }
}

function ensureReferences(
  references: readonly string[],
  knownIds: readonly string[],
  kind: string,
): void {
  const known = new Set(knownIds);
  const counts = new Map<string, number>();
  for (const reference of references) {
    if (!known.has(reference)) {
      throw new Error(`Invalid dashboard clarity ${kind} reference "${reference}": unknown id`);
    }
    counts.set(reference, (counts.get(reference) ?? 0) + 1);
  }
  for (const id of knownIds) {
    const count = counts.get(id) ?? 0;
    if (count !== 1) {
      throw new Error(`Invalid dashboard clarity ${kind} reference "${id}": expected exactly once, received ${count}`);
    }
  }
}

export function enrichInfoPanel(
  value: unknown,
  clarityValue: unknown,
  overlayLastUpdated?: string,
): InfoPanel {
  const raw = validateRawInfoPanel(value, 'enrichment');
  const clarity = validateClarity(clarityValue, 'enrichment');

  ensureKnownOverrides(clarity.statOverrides, raw.stats.map((stat) => stat.label), 'stat');
  ensureKnownOverrides(clarity.chartOverrides, raw.charts.map((chart) => chart.title), 'chart');
  ensureKnownOverrides(clarity.tableIds, (raw.tables ?? []).map((table) => table.title), 'table');

  const stats: InfoStat[] = raw.stats.map((stat) => {
    const id = stableDashboardId(stat.label);
    const override = clarity.statOverrides[stat.label];
    return {
      ...stat,
      id,
      priority: override?.priority === true,
      ...(override?.label ? { label: override.label } : {}),
      ...(override?.hint ? { hint: override.hint } : {}),
    };
  });
  const charts: InfoChart[] = raw.charts.map((chart) => {
    const override = clarity.chartOverrides[chart.title];
    if (!override?.takeaway) {
      throw new Error(`Invalid dashboard clarity chart "${chart.title}": missing takeaway`);
    }
    return {
      ...chart,
      id: stableDashboardId(chart.title),
      takeaway: override.takeaway,
      ...(override.title ? { title: override.title } : {}),
    };
  });
  const tables: InfoTable[] = (raw.tables ?? []).map((table) => {
    const id = clarity.tableIds[table.title];
    if (!id) throw new Error(`Invalid dashboard clarity table "${table.title}": missing id`);
    return { ...table, id };
  });

  ensureUniqueIds(stats, 'stats');
  ensureUniqueIds(charts, 'charts');
  ensureUniqueIds(tables, 'tables');

  const priorityIds = stats.filter((stat) => stat.priority).map((stat) => stat.id as string);
  if (priorityIds.length > 4) throw new Error('Invalid dashboard clarity stats: more than four priority facts');
  ensureReferences(
    [...priorityIds, ...clarity.sections.flatMap((section) => section.stats ?? [])],
    stats.map((stat) => stat.id as string),
    'stats',
  );
  ensureReferences(
    clarity.sections.flatMap((section) => section.charts ?? []),
    charts.map((chart) => chart.id as string),
    'charts',
  );
  ensureReferences(
    clarity.sections.flatMap((section) => section.tables ?? []),
    tables.map((table) => table.id as string),
    'tables',
  );

  return {
    ...raw,
    ...(clarity.title ? { title: clarity.title } : {}),
    ...(clarity.subtitle ? { subtitle: clarity.subtitle } : {}),
    summary: clarity.summary,
    stats,
    charts,
    tables,
    lastUpdated: raw.lastUpdated ?? overlayLastUpdated,
    context: clarity.context,
    headline: clarity.headline,
    responsibility: clarity.responsibility,
    action: clarity.action,
    sections: clarity.sections,
  };
}
