import { describe, expect, it, vi } from 'vitest';
import { createDashboardData } from '../src/lib/dashboard/dashboardData.svelte';

const panel = (title: string) => ({ title, stats: [], charts: [] });

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

  it('loads one validated panel and applies shared metadata without mutating it', async () => {
    const source = panel('Finances');
    const fetcher = vi.fn(async (url: string) => {
      if (url === 'info-finances.json') return jsonResponse(source);
      if (url === 'summaries.json') return jsonResponse({ finances: { body: ['Summary'] } });
      if (url === 'freshness.json') return jsonResponse({ finances: '2026-06' });
      throw new Error(`Unexpected URL: ${url}`);
    });
    const data = createDashboardData(['finances'], {
      fetch: fetcher,
      prefetchAdjacent: false,
    });

    const loaded = await data.load('finances');

    expect(loaded).toEqual({
      ...source,
      summary: { body: ['Summary'] },
      lastUpdated: '2026-06',
    });
    expect(loaded).not.toBe(source);
    expect(source).toEqual(panel('Finances'));
    expect(data.state('finances')).toMatchObject({ panel: loaded, loading: false, error: null });
  });

  it('deduplicates concurrent loads and caches a successful result', async () => {
    const pending = deferred<Response>();
    const fetcher = vi.fn((url: string) => {
      if (url === 'info-finances.json') return pending.promise;
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

  it('distinguishes missing, transient HTTP, network, and validation failures', async () => {
    const fetcher = vi.fn(async (url: string) => {
      if (url === 'info-finances.json') return jsonResponse({}, 404);
      if (url === 'info-health.json') throw new TypeError('offline');
      if (url === 'info-roads.json') return jsonResponse({ title: 'Roads', stats: [], charts: [{ type: 'pie', title: 'Bad' }] });
      if (url === 'info-water.json') return jsonResponse({}, 503);
      return jsonResponse({});
    });
    const data = createDashboardData(['finances', 'health', 'roads', 'water'], {
      fetch: fetcher,
      prefetchAdjacent: false,
    });

    await Promise.all([
      data.load('finances'),
      data.load('health'),
      data.load('roads'),
      data.load('water'),
    ]);

    expect(data.state('finances').error?.kind).toBe('missing');
    expect(data.state('health').error?.kind).toBe('network');
    expect(data.state('roads').error?.kind).toBe('validation');
    expect(data.state('water').error?.kind).toBe('http');
  });

  it('retries only the requested failed dashboard', async () => {
    let healthAttempts = 0;
    const fetcher = vi.fn(async (url: string) => {
      if (url === 'info-finances.json') return jsonResponse(panel('Finances'), 404);
      if (url === 'info-health.json') {
        healthAttempts += 1;
        return healthAttempts === 1
          ? jsonResponse({}, 503)
          : jsonResponse(panel('Health'));
      }
      return jsonResponse({});
    });
    const data = createDashboardData(['finances', 'health'], {
      fetch: fetcher,
      prefetchAdjacent: false,
    });
    await Promise.all([data.load('finances'), data.load('health')]);
    expect(data.state('health').error?.kind).toBe('http');

    await data.retry('health');

    expect(data.state('health').panel?.title).toBe('Health');
    expect(fetcher.mock.calls.filter(([url]) => url === 'info-health.json')).toHaveLength(2);
    expect(fetcher.mock.calls.filter(([url]) => url === 'info-finances.json')).toHaveLength(1);
  });

  it('keeps rapid navigation results isolated by dashboard id', async () => {
    const finances = deferred<Response>();
    const health = deferred<Response>();
    const fetcher = vi.fn((url: string) => {
      if (url === 'info-finances.json') return finances.promise;
      if (url === 'info-health.json') return health.promise;
      return Promise.resolve(jsonResponse({}));
    });
    const data = createDashboardData(['finances', 'health'], {
      fetch: fetcher,
      prefetchAdjacent: false,
    });

    const slowFirst = data.load('finances');
    const fastSecond = data.load('health');
    health.resolve(jsonResponse(panel('Health')));
    await fastSecond;
    finances.resolve(jsonResponse(panel('Finances')));
    await slowFirst;

    expect(data.state('finances').panel?.title).toBe('Finances');
    expect(data.state('health').panel?.title).toBe('Health');
  });

  it('fetches metadata once across multiple dashboard loads', async () => {
    const fetcher = vi.fn(async (url: string) => {
      if (url.startsWith('info-')) return jsonResponse(panel(url));
      return jsonResponse({});
    });
    const data = createDashboardData(['finances', 'health'], {
      fetch: fetcher,
      prefetchAdjacent: false,
    });

    await data.load('finances');
    await data.load('health');

    expect(fetcher.mock.calls.filter(([url]) => url === 'summaries.json')).toHaveLength(1);
    expect(fetcher.mock.calls.filter(([url]) => url === 'freshness.json')).toHaveLength(1);
  });

  it('prefetches only the immediately following dashboard when online', async () => {
    const fetcher = vi.fn(async (url: string) => {
      if (url.startsWith('info-')) return jsonResponse(panel(url));
      return jsonResponse({});
    });
    const data = createDashboardData(['finances', 'health', 'roads'], {
      fetch: fetcher,
      isOnline: () => true,
    });

    await data.load('finances');
    await vi.waitFor(() => expect(data.state('health').panel).not.toBeNull());

    expect(data.state('roads').requested).toBe(false);
    expect(fetcher.mock.calls.filter(([url]) => url.startsWith('info-')).map(([url]) => url)).toEqual([
      'info-finances.json',
      'info-health.json',
    ]);
  });

  it('does not prefetch while offline', async () => {
    const fetcher = vi.fn(async (url: string) => {
      if (url.startsWith('info-')) return jsonResponse(panel(url));
      return jsonResponse({});
    });
    const data = createDashboardData(['finances', 'health'], {
      fetch: fetcher,
      isOnline: () => false,
    });

    await data.load('finances');

    expect(data.state('health').requested).toBe(false);
  });

  it('loads all dashboards only when Open Data explicitly requests them', async () => {
    const fetcher = vi.fn(async (url: string) => {
      if (url.startsWith('info-')) return jsonResponse(panel(url));
      return jsonResponse({});
    });
    const data = createDashboardData(['finances', 'health'], { fetch: fetcher });

    await data.loadAll();

    expect(data.allLoaded).toBe(true);
    expect(data.panels.finances?.title).toBe('info-finances.json');
    expect(data.panels.health?.title).toBe('info-health.json');
  });
});
