import type {
  CompareRow,
  CompareValue,
  EstimatorDistrict,
  InfoChart,
  InfoEstimator,
  InfoExplainer,
  InfoExplainerItem,
  InfoLink,
  InfoPanel,
  InfoSeriesItem,
  InfoStat,
  InfoSummary,
  InfoTable,
  InfoTableRow,
} from '../types';

export type {
  CompareRow,
  CompareValue,
  EstimatorDistrict,
  InfoChart,
  InfoEstimator,
  InfoExplainer,
  InfoExplainerItem,
  InfoLink,
  InfoPanel,
  InfoSeriesItem,
  InfoStat,
  InfoSummary,
  InfoTable,
  InfoTableRow,
} from '../types';

type JsonObject = Record<string, unknown>;

function fail(context: string, path: string, expectation: string): never {
  throw new Error(`Invalid ${context} at ${path}: ${expectation}`);
}

function objectValue(value: unknown, context: string, path: string): JsonObject {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    fail(context, path, 'expected an object');
  }
  return value as JsonObject;
}

function arrayValue(value: unknown, context: string, path: string): unknown[] {
  if (!Array.isArray(value)) fail(context, path, 'expected an array');
  return value;
}

function stringValue(value: unknown, context: string, path: string): string {
  if (typeof value !== 'string' || value.length === 0) {
    fail(context, path, 'expected a non-empty string');
  }
  return value;
}

function textValue(value: unknown, context: string, path: string): string {
  if (typeof value !== 'string') fail(context, path, 'expected a string');
  return value;
}

function optionalString(value: unknown, context: string, path: string): void {
  if (value !== undefined) stringValue(value, context, path);
}

function optionalUnit(value: unknown, context: string, path: string): void {
  if (value !== undefined && typeof value !== 'string') {
    fail(context, path, 'expected a string');
  }
}

function numberValue(value: unknown, context: string, path: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    fail(context, path, 'expected a finite number');
  }
  return value;
}

function stringArray(value: unknown, context: string, path: string): string[] {
  return arrayValue(value, context, path).map((item, index) =>
    stringValue(item, context, `${path}[${index}]`),
  );
}

function textArray(value: unknown, context: string, path: string): string[] {
  return arrayValue(value, context, path).map((item, index) =>
    textValue(item, context, `${path}[${index}]`),
  );
}

function uniqueObjectField(
  items: readonly unknown[],
  field: string,
  context: string,
  path: string,
): void {
  const seen = new Set<string>();
  items.forEach((item, index) => {
    const value = objectValue(item, context, `${path}[${index}]`)[field];
    if (typeof value !== 'string') return;
    if (seen.has(value)) {
      fail(context, `${path}[${index}].${field}`, `duplicate value "${value}"`);
    }
    seen.add(value);
  });
}

function uniqueStrings(
  items: readonly string[],
  context: string,
  path: string,
): void {
  const seen = new Set<string>();
  items.forEach((value, index) => {
    if (seen.has(value)) fail(context, `${path}[${index}]`, `duplicate value "${value}"`);
    seen.add(value);
  });
}

function validatePoint(value: unknown, context: string, path: string): void {
  const point = objectValue(value, context, path);
  stringValue(point.x, context, `${path}.x`);
  numberValue(point.y, context, `${path}.y`);
}

function validateCompareValue(value: unknown, context: string, path: string): void {
  const item = objectValue(value, context, path) as Partial<CompareValue>;
  stringValue(item.name, context, `${path}.name`);
  numberValue(item.value, context, `${path}.value`);
}

function validateCompareRow(value: unknown, context: string, path: string): void {
  const row = objectValue(value, context, path) as Partial<CompareRow>;
  stringValue(row.label, context, `${path}.label`);
  optionalUnit(row.unit, context, `${path}.unit`);
  const values = arrayValue(row.values, context, `${path}.values`);
  values.forEach((item, index) =>
    validateCompareValue(item, context, `${path}.values[${index}]`),
  );
  uniqueObjectField(values, 'name', context, `${path}.values`);
  if (row.cities !== undefined) {
    const cities = arrayValue(row.cities, context, `${path}.cities`);
    cities.forEach((item, index) =>
      validateCompareValue(item, context, `${path}.cities[${index}]`),
    );
    uniqueObjectField(cities, 'name', context, `${path}.cities`);
  }
}

function validateSeriesItem(value: unknown, context: string, path: string): void {
  const item = objectValue(value, context, path) as Partial<InfoSeriesItem>;
  stringValue(item.label, context, `${path}.label`);
  numberValue(item.value, context, `${path}.value`);
  optionalString(item.color, context, `${path}.color`);
}

function validateChart(value: unknown, context: string, path: string): void {
  const chart = objectValue(value, context, path) as Partial<InfoChart> & JsonObject;
  const type = stringValue(chart.type, context, `${path}.type`);
  stringValue(chart.title, context, `${path}.title`);
  optionalUnit(chart.unit, context, `${path}.unit`);
  optionalString(chart.citiesLede, context, `${path}.citiesLede`);

  if (type === 'donut' || type === 'bars') {
    const series = arrayValue(chart.series, context, `${path}.series`);
    series.forEach((item, index) =>
      validateSeriesItem(item, context, `${path}.series[${index}]`),
    );
    uniqueObjectField(series, 'label', context, `${path}.series`);
    return;
  }

  if (type === 'trend') {
    const points = chart.points === undefined
      ? []
      : arrayValue(chart.points, context, `${path}.points`);
    const lines = chart.lines === undefined
      ? []
      : arrayValue(chart.lines, context, `${path}.lines`);
    if (points.length === 0 && lines.length === 0) {
      fail(context, path, 'trend chart requires points or lines');
    }
    points.forEach((item, index) => validatePoint(item, context, `${path}.points[${index}]`));
    uniqueObjectField(points, 'x', context, `${path}.points`);
    lines.forEach((item, index) => {
      const linePath = `${path}.lines[${index}]`;
      const line = objectValue(item, context, linePath);
      stringValue(line.label, context, `${linePath}.label`);
      optionalString(line.color, context, `${linePath}.color`);
      const linePoints = arrayValue(line.points, context, `${linePath}.points`);
      linePoints.forEach((point, pointIndex) =>
        validatePoint(point, context, `${linePath}.points[${pointIndex}]`),
      );
      uniqueObjectField(linePoints, 'x', context, `${linePath}.points`);
    });
    uniqueObjectField(lines, 'label', context, `${path}.lines`);
    if (chart.markers !== undefined) {
      const markers = arrayValue(chart.markers, context, `${path}.markers`);
      markers.forEach((item, index) => {
        const markerPath = `${path}.markers[${index}]`;
        const marker = objectValue(item, context, markerPath);
        stringValue(marker.x, context, `${markerPath}.x`);
        stringValue(marker.label, context, `${markerPath}.label`);
      });
      uniqueObjectField(markers, 'x', context, `${path}.markers`);
    }
    return;
  }

  if (type === 'compare') {
    const rows = arrayValue(chart.rows, context, `${path}.rows`);
    rows.forEach((item, index) =>
      validateCompareRow(item, context, `${path}.rows[${index}]`),
    );
    uniqueObjectField(rows, 'label', context, `${path}.rows`);
    return;
  }

  fail(context, `${path}.type`, `unknown chart type "${type}"`);
}

function validateStat(value: unknown, context: string, path: string): void {
  const stat = objectValue(value, context, path) as Partial<InfoStat>;
  stringValue(stat.label, context, `${path}.label`);
  stringValue(stat.value, context, `${path}.value`);
  optionalString(stat.hint, context, `${path}.hint`);

  if (stat.benchmarks !== undefined) {
    const benchmarks = arrayValue(stat.benchmarks, context, `${path}.benchmarks`);
    benchmarks.forEach((item, index) => {
      const benchmarkPath = `${path}.benchmarks[${index}]`;
      const benchmark = objectValue(item, context, benchmarkPath);
      stringValue(benchmark.name, context, `${benchmarkPath}.name`);
      stringValue(benchmark.value, context, `${benchmarkPath}.value`);
    });
    uniqueObjectField(benchmarks, 'name', context, `${path}.benchmarks`);
  }
  if (stat.spark !== undefined) {
    arrayValue(stat.spark, context, `${path}.spark`).forEach((item, index) =>
      validatePoint(item, context, `${path}.spark[${index}]`),
    );
  }
}

function validateSummary(value: unknown, context: string, path: string): void {
  const summary = objectValue(value, context, path) as Partial<InfoSummary>;
  optionalString(summary.heading, context, `${path}.heading`);
  stringArray(summary.body, context, `${path}.body`);
}

function validateExplainer(value: unknown, context: string, path: string): void {
  const explainer = objectValue(value, context, path) as Partial<InfoExplainer>;
  stringValue(explainer.title, context, `${path}.title`);
  optionalString(explainer.intro, context, `${path}.intro`);
  optionalString(explainer.source, context, `${path}.source`);
  const items = arrayValue(explainer.items, context, `${path}.items`);
  items.forEach((item, index) => {
    const itemPath = `${path}.items[${index}]`;
    const explainerItem = objectValue(item, context, itemPath) as Partial<InfoExplainerItem>;
    stringValue(explainerItem.term, context, `${itemPath}.term`);
    stringValue(explainerItem.body, context, `${itemPath}.body`);
  });
  uniqueObjectField(items, 'term', context, `${path}.items`);
}

function validateEstimator(value: unknown, context: string, path: string): void {
  const estimator = objectValue(value, context, path) as Partial<InfoEstimator>;
  numberValue(estimator.cityMills, context, `${path}.cityMills`);
  numberValue(estimator.countyMills, context, `${path}.countyMills`);
  const districts = arrayValue(estimator.districts, context, `${path}.districts`);
  districts.forEach((item, index) => {
    const districtPath = `${path}.districts[${index}]`;
    const district = objectValue(item, context, districtPath) as Partial<EstimatorDistrict>;
    stringValue(district.name, context, `${districtPath}.name`);
    numberValue(district.homestead, context, `${districtPath}.homestead`);
    numberValue(district.nonHomestead, context, `${districtPath}.nonHomestead`);
  });
  uniqueObjectField(districts, 'name', context, `${path}.districts`);
}

function validateTable(value: unknown, context: string, path: string): void {
  const table = objectValue(value, context, path) as Partial<InfoTable>;
  stringValue(table.title, context, `${path}.title`);
  const columns = stringArray(table.columns, context, `${path}.columns`);
  uniqueStrings(columns, context, `${path}.columns`);
  arrayValue(table.rows, context, `${path}.rows`).forEach((item, index) => {
    const rowPath = `${path}.rows[${index}]`;
    const row = objectValue(item, context, rowPath) as Partial<InfoTableRow>;
    const cells = textArray(row.cells, context, `${rowPath}.cells`);
    if (cells.length !== columns.length) {
      fail(context, `${rowPath}.cells`, `expected ${columns.length} columns, received ${cells.length}`);
    }
    optionalString(row.color, context, `${rowPath}.color`);
  });
}

function validateLink(value: unknown, context: string, path: string): void {
  const link = objectValue(value, context, path) as Partial<InfoLink>;
  stringValue(link.text, context, `${path}.text`);
  stringValue(link.href, context, `${path}.href`);
}

function validateIsoDate(value: unknown, context: string, path: string): void {
  const date = stringValue(value, context, path);
  const match = /^(\d{4})-(\d{2})(?:-(\d{2}))?$/.exec(date);
  if (!match) fail(context, path, 'expected an ISO date in YYYY-MM or YYYY-MM-DD format');

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = match[3] === undefined ? 1 : Number(match[3]);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  if (
    parsed.getUTCFullYear() !== year ||
    parsed.getUTCMonth() !== month - 1 ||
    parsed.getUTCDate() !== day
  ) {
    fail(context, path, 'expected a valid ISO date in YYYY-MM or YYYY-MM-DD format');
  }
}

/** Validate untrusted dashboard JSON before it reaches a renderer. */
export function validateInfoPanel(value: unknown, id: string): InfoPanel {
  const context = `dashboard "${id}"`;
  const panel = objectValue(value, context, '$') as Partial<InfoPanel> & JsonObject;

  stringValue(panel.title, context, 'title');
  optionalString(panel.subtitle, context, 'subtitle');
  optionalString(panel.logo, context, 'logo');
  if (panel.draft !== undefined && typeof panel.draft !== 'boolean') {
    fail(context, 'draft', 'expected a boolean');
  }
  optionalString(panel.draftNote, context, 'draftNote');
  if (panel.summary !== undefined) validateSummary(panel.summary, context, 'summary');
  if (panel.explainer !== undefined) validateExplainer(panel.explainer, context, 'explainer');
  if (panel.methodology !== undefined) {
    const methodology = objectValue(panel.methodology, context, 'methodology');
    optionalString(methodology.title, context, 'methodology.title');
    stringValue(methodology.body, context, 'methodology.body');
  }
  if (panel.estimator !== undefined) validateEstimator(panel.estimator, context, 'estimator');
  const stats = arrayValue(panel.stats, context, 'stats');
  stats.forEach((item, index) =>
    validateStat(item, context, `stats[${index}]`),
  );
  uniqueObjectField(stats, 'label', context, 'stats');
  const charts = arrayValue(panel.charts, context, 'charts');
  charts.forEach((item, index) =>
    validateChart(item, context, `charts[${index}]`),
  );
  uniqueObjectField(charts, 'title', context, 'charts');
  if (panel.tables !== undefined) {
    const tables = arrayValue(panel.tables, context, 'tables');
    tables.forEach((item, index) =>
      validateTable(item, context, `tables[${index}]`),
    );
    uniqueObjectField(tables, 'title', context, 'tables');
  }
  if (panel.lastUpdated !== undefined) validateIsoDate(panel.lastUpdated, context, 'lastUpdated');
  optionalString(panel.source, context, 'source');
  if (panel.links !== undefined) {
    const links = arrayValue(panel.links, context, 'links');
    links.forEach((item, index) =>
      validateLink(item, context, `links[${index}]`),
    );
    uniqueObjectField(links, 'href', context, 'links');
  }
  if (panel.notes !== undefined) stringArray(panel.notes, context, 'notes');

  return value as InfoPanel;
}

export function validateSummaryMap(
  value: unknown,
  dashboardIds: readonly string[],
): Record<string, InfoSummary> {
  const summaries = objectValue(value, 'dashboard metadata', 'summaries');
  const knownIds = new Set(dashboardIds);
  for (const [id, summary] of Object.entries(summaries)) {
    if (id.startsWith('_')) continue;
    if (!knownIds.has(id)) {
      fail('dashboard metadata', `summaries.${id}`, 'expected a registered dashboard id');
    }
    validateSummary(summary, 'dashboard metadata', `summaries.${id}`);
  }
  return value as Record<string, InfoSummary>;
}

export function validateFreshnessMap(
  value: unknown,
  dashboardIds: readonly string[],
): Record<string, string> {
  const freshness = objectValue(value, 'dashboard metadata', 'freshness');
  const knownIds = new Set(dashboardIds);
  for (const [id, date] of Object.entries(freshness)) {
    if (id.startsWith('_')) {
      stringValue(date, 'dashboard metadata', `freshness.${id}`);
      continue;
    }
    if (!knownIds.has(id)) {
      fail('dashboard metadata', `freshness.${id}`, 'expected a registered dashboard id');
    }
    validateIsoDate(date, 'dashboard metadata', `freshness.${id}`);
  }
  return value as Record<string, string>;
}
