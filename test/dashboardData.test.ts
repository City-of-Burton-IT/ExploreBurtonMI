import { describe, expect, it, vi } from 'vitest';
import { createDashboardData } from '../src/lib/dashboard/dashboardData.svelte';

const panel = (title: string) => ({
  title,
  stats: [{ label: 'Residents', value: '1,000' }],
  charts: [{ type: 'bars', title: 'Count', series: [{ label: 'Total', value: 10 }] }],
});

const clarity = (headline = 'The dashboard highlights the most important local finding.') => ({
  context: { scope: 'City of Burton', status: 'current', asOf: 'June 2026' },
  headline,
  summary: { heading: 'Why this matters', body: ['This short explanation describes the finding.'] },
  responsibility: 'The City reports this measure and explains which agency controls it.',
  action: { kind: 'none', text: 'No direct resident action is needed.' },
  statOverrides: { Residents: { priority: true } },
  chartOverrides: { Count: { takeaway: 'The chart contains ten recorded items.' } },
  tableIds: {},
  sections: [{ heading: 'Evidence', charts: ['count'] }],
});

function clarityMap(ids: readonly string[]) {
  return Object.fromEntries(ids.map((id) => [id, clarity()]));
}

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe('createDashboardData', () => {
  it('requests no dashboard or metadata files until explicitly loaded', () => {
    const fetcher = vi.fn(async () => jsonResponse({}));
    createDashboardData(['finances', 'health'], { fetch: fetcher });
    expect(fetcher).not.toHaveBeenCalled();
  });

  it('loads one raw panel, applies clarity and freshness, and validates the result', async () => {
    const source = panel('Finances');
    const financeClarity = clarity(
      'Burton adopted a $67.7 million all-funds plan for FY2026–27.',
    );
    const fetcher = vi.fn(async (url: string) => {
      if (url === 'info-finances.json') return jsonResponse(source);
      if (url === 'dashboard-clarity.json') {
        return jsonResponse({ finances: financeClarity });
      }
      if (url === 'freshness.json') return jsonResponse({ finances: '2026-06' });
      throw new Error(`Unexpected URL: ${url}`);
    });
    const data = createDashboardData(['finances'], {
      fetch: fetcher,
      prefetchAdjacent: false,
    });

    const loaded = await data.load('finances');

    expect(loaded).toMatchObject({
      title: 'Finances',
      headline: financeClarity.headline,
      context: financeClarity.context,
      lastUpdated: '2026-06',
      stats: [{ id: 'residents', label: 'Residents', priority: true }],
      charts: [{ id: 'count', takeaway: 'The chart contains ten recorded items.' }],
    });
    expect(loaded).not.toBe(source);
    expect(source).toEqual(panel('Finances'));
    expect(data.state('finances')).toMatchObject({ panel: loaded, loading: false, error: null });
  });

  it('reports a validation failure when a registered dashboard has no clarity record', async () => {
    const fetcher = vi.fn(async (url: string) => {
      if (url === 'info-finances.json') return jsonResponse(panel('Finances'));
      if (url === 'dashboard-clarity.json') return jsonResponse({});
      return jsonResponse({});
    });
    const data = createDashboardData(['finances'], { fetch: fetcher, prefetchAdjacent: false });

    expect(await data.load('finances')).toBeNull();
    expect(data.state('finances').error).toMatchObject({ kind: 'validation' });
  });

  it('deduplicates concurrent loads and caches a successful result', async () => {
    const pending = deferred<Response>();
    const fetcher = vi.fn((url: string) => {
      if (url === 'info-finances.json') return pending.promise;
      if (url === 'dashboard-clarity.json') {
        return Promise.resolve(jsonResponse(clarityMap(['finances'])));
      }
      return Promise.resolve(jsonResponse({}));
    });
    const data = createDashboardData(['finances'], {
      fetch: fetcher,
      prefetchAdjacent: false,
    });

    const first = data.load('finances');
    const second = data.load('finances');
    expect(data.state('finances').loading).toBe(true);
    pending.resolve(jsonResponse(panel('Finances')));

    expect(await first).toBe(await second);
    await data.load('finances');
    expect(fetcher.mock.calls.filter(([url]) => url === 'info-finances.json')).toHaveLength(1);
  });

  it('distinguishes missing, transient HTTP, network, and raw validation failures', async () => {
    const ids = ['finances', 'health', 'roads', 'water'];
    const fetcher = vi.fn(async (url: string) => {
      if (url === 'info-finances.json') return jsonResponse({}, 404);
      if (url === 'info-health.json') throw new TypeError('offline');
      if (url === 'info-roads.json') {
        return jsonResponse({ title: 'Roads', stats: [], charts: [{ type: 'pie', title: 'Bad' }] });
      }
      if (url === 'info-water.json') return jsonResponse({}, 503);
      if (url === 'dashboard-clarity.json') return jsonResponse(clarityMap(ids));
      return jsonResponse({});
    });
    const data = createDashboardData(ids, { fetch: fetcher, prefetchAdjacent: false });

    await Promise.all(ids.map((id) => data.load(id)));

    expect(data.state('finances').error?.kind).toBe('missing');
    expect(data.state('health').error?.kind).toBe('network');
    expect(data.state('roads').error?.kind).toBe('validation');
    expect(data.state('water').error?.kind).toBe('http');
  });

  it('retries only the requested failed dashboard', async () => {
    const ids = ['finances', 'health'];
    let healthAttempts = 0;
    const fetcher = vi.fn(async (url: string) => {
      if (url === 'info-finances.json') return jsonResponse(panel('Finances'), 404);
      if (url === 'info-health.json') {
        healthAttempts += 1;
        return healthAttempts === 1 ? jsonResponse({}, 503) : jsonResponse(panel('Health'));
      }
      if (url === 'dashboard-clarity.json') return jsonResponse(clarityMap(ids));
      return jsonResponse({});
    });
    const data = createDashboardData(ids, { fetch: fetcher, prefetchAdjacent: false });
    await Promise.all([data.load('finances'), data.load('health')]);
    expect(data.state('health').error?.kind).toBe('http');

    await data.retry('health');

    expect(data.state('health').panel?.title).toBe('Health');
    expect(fetcher.mock.calls.filter(([url]) => url === 'info-health.json')).toHaveLength(2);
    expect(fetcher.mock.calls.filter(([url]) => url === 'info-finances.json')).toHaveLength(1);
  });

  it('keeps rapid navigation results isolated by dashboard id', async () => {
    const ids = ['finances', 'health'];
    const finances = deferred<Response>();
    const health = deferred<Response>();
    const fetcher = vi.fn((url: string) => {
      if (url === 'info-finances.json') return finances.promise;
      if (url === 'info-health.json') return health.promise;
      if (url === 'dashboard-clarity.json') {
        return Promise.resolve(jsonResponse(clarityMap(ids)));
      }
      return Promise.resolve(jsonResponse({}));
    });
    const data = createDashboardData(ids, { fetch: fetcher, prefetchAdjacent: false });

    const slowFirst = data.load('finances');
    const fastSecond = data.load('health');
    health.resolve(jsonResponse(panel('Health')));
    await fastSecond;
    finances.resolve(jsonResponse(panel('Finances')));
    await slowFirst;

    expect(data.state('finances').panel?.title).toBe('Finances');
    expect(data.state('health').panel?.title).toBe('Health');
  });

  it('fetches clarity and freshness metadata once across multiple dashboard loads', async () => {
    const ids = ['finances', 'health'];
    const fetcher = vi.fn(async (url: string) => {
      if (url.startsWith('info-')) return jsonResponse(panel(url));
      if (url === 'dashboard-clarity.json') return jsonResponse(clarityMap(ids));
      return jsonResponse({});
    });
    const data = createDashboardData(ids, { fetch: fetcher, prefetchAdjacent: false });

    await data.load('finances');
    await data.load('health');

    expect(fetcher.mock.calls.filter(([url]) => url === 'dashboard-clarity.json')).toHaveLength(1);
    expect(fetcher.mock.calls.filter(([url]) => url === 'freshness.json')).toHaveLength(1);
  });

  it('prefetches only the immediately following dashboard when online', async () => {
    const ids = ['finances', 'health', 'roads'];
    const fetcher = vi.fn(async (url: string) => {
      if (url.startsWith('info-')) return jsonResponse(panel(url));
      if (url === 'dashboard-clarity.json') return jsonResponse(clarityMap(ids));
      return jsonResponse({});
    });
    const data = createDashboardData(ids, { fetch: fetcher, isOnline: () => true });

    await data.load('finances');
    await vi.waitFor(() => expect(data.state('health').panel).not.toBeNull());

    expect(data.state('roads').requested).toBe(false);
    expect(fetcher.mock.calls.filter(([url]) => url.startsWith('info-')).map(([url]) => url)).toEqual([
      'info-finances.json',
      'info-health.json',
    ]);
  });

  it('does not prefetch while offline', async () => {
    const ids = ['finances', 'health'];
    const fetcher = vi.fn(async (url: string) => {
      if (url.startsWith('info-')) return jsonResponse(panel(url));
      if (url === 'dashboard-clarity.json') return jsonResponse(clarityMap(ids));
      return jsonResponse({});
    });
    const data = createDashboardData(ids, { fetch: fetcher, isOnline: () => false });

    await data.load('finances');

    expect(data.state('health').requested).toBe(false);
  });

  it('loads all dashboards only when Open Data explicitly requests them', async () => {
    const ids = ['finances', 'health'];
    const fetcher = vi.fn(async (url: string) => {
      if (url.startsWith('info-')) return jsonResponse(panel(url));
      if (url === 'dashboard-clarity.json') return jsonResponse(clarityMap(ids));
      return jsonResponse({});
    });
    const data = createDashboardData(ids, { fetch: fetcher });

    await data.loadAll();

    expect(data.allLoaded).toBe(true);
    expect(data.panels.finances?.title).toBe('info-finances.json');
    expect(data.panels.health?.title).toBe('info-health.json');
  });
});
