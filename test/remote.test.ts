import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// remote.ts reads Capacitor.isNativePlatform() once at module load, so each
// scenario needs a fresh module registry (vi.resetModules) plus its own mock
// of '@capacitor/core' before the dynamic import.

const REMOTE_BASE = 'https://explore.burtonmi.gov/';

async function loadDataFetch(isNative: boolean): Promise<typeof import('../src/lib/remote').dataFetch> {
  vi.resetModules();
  vi.doMock('@capacitor/core', () => ({
    Capacitor: { isNativePlatform: () => isNative },
  }));
  const mod = await import('../src/lib/remote');
  return mod.dataFetch;
}

describe('dataFetch', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.doUnmock('@capacitor/core');
  });

  it('web platform: plain fetch of the relative path', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true } as Response);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const dataFetch = await loadDataFetch(false);
    const res = await dataFetch('data.json');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith('data.json');
    expect(res.ok).toBe(true);
  });

  it('native: tries the remote site first and returns it when ok', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, marker: 'remote' } as unknown as Response);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const dataFetch = await loadDataFetch(true);
    const res = await dataFetch('./data.json');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [calledUrl] = fetchMock.mock.calls[0];
    expect(calledUrl).toBe(`${REMOTE_BASE}data.json`);
    expect((res as unknown as { marker: string }).marker).toBe('remote');
  });

  it('native + remote responds non-OK: falls back to the bundled path', async () => {
    const fetchMock = vi.fn();
    // 1st call: remote, not ok. 2nd call: bundled path, ok.
    fetchMock
      .mockResolvedValueOnce({ ok: false } as Response)
      .mockResolvedValueOnce({ ok: true, marker: 'bundled' } as unknown as Response);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const dataFetch = await loadDataFetch(true);
    const res = await dataFetch('data.json');

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toBe(`${REMOTE_BASE}data.json`);
    expect(fetchMock.mock.calls[1][0]).toBe('data.json');
    expect((res as unknown as { marker: string }).marker).toBe('bundled');
  });

  it('native + remote fetch rejects: falls back to the bundled path', async () => {
    const fetchMock = vi.fn();
    fetchMock
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce({ ok: true, marker: 'bundled' } as unknown as Response);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const dataFetch = await loadDataFetch(true);
    const res = await dataFetch('data.json');

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][0]).toBe('data.json');
    expect((res as unknown as { marker: string }).marker).toBe('bundled');
  });

  it('absolute URLs bypass the remote-first logic even natively', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true } as Response);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const dataFetch = await loadDataFetch(true);
    const url = 'https://api.example.com/thing.json';
    await dataFetch(url);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(url);
  });

  it('absolute http URLs also bypass remote-first on the web', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true } as Response);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const dataFetch = await loadDataFetch(false);
    const url = 'http://api.example.com/thing.json';
    await dataFetch(url);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(url);
  });
});
