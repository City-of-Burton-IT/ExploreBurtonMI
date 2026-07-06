import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// comingSoon.ts reads Capacitor.isNativePlatform() once at module load (same
// pattern as remote.ts), so each scenario needs a fresh module registry plus
// its own mock of '@capacitor/core' before the dynamic import.

const STORAGE_KEY = 'eb-unlocked';
const UNLOCK_PHRASE = 'burton-preview';

/** Minimal in-memory localStorage shim. `throwing` makes every call throw, to
 *  exercise the module's private-mode / storage-disabled guard paths. */
function makeLocalStorage(opts: { throwing?: boolean } = {}) {
  const store = new Map<string, string>();
  return {
    getItem(key: string): string | null {
      if (opts.throwing) throw new Error('storage disabled');
      return store.has(key) ? store.get(key)! : null;
    },
    setItem(key: string, value: string): void {
      if (opts.throwing) throw new Error('storage disabled');
      store.set(key, value);
    },
    removeItem(key: string): void {
      if (opts.throwing) throw new Error('storage disabled');
      store.delete(key);
    },
    clear(): void {
      store.clear();
    },
    _store: store,
  };
}

async function loadComingSoon(isNative: boolean): Promise<typeof import('../src/lib/comingSoon')> {
  vi.resetModules();
  vi.doMock('@capacitor/core', () => ({
    Capacitor: { isNativePlatform: () => isNative },
  }));
  return import('../src/lib/comingSoon');
}

describe('comingSoon', () => {
  const originalLocalStorage = (globalThis as { localStorage?: unknown }).localStorage;
  const originalWindow = (globalThis as { window?: unknown }).window;

  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    (globalThis as { localStorage?: unknown }).localStorage = originalLocalStorage;
    (globalThis as { window?: unknown }).window = originalWindow;
    vi.doUnmock('@capacitor/core');
  });

  describe('isUnlocked', () => {
    it('is false when nothing is stored', async () => {
      (globalThis as unknown as { localStorage: unknown }).localStorage = makeLocalStorage();
      const { isUnlocked } = await loadComingSoon(false);
      expect(isUnlocked()).toBe(false);
    });

    it('is true once the unlock flag is persisted', async () => {
      const ls = makeLocalStorage();
      ls._store.set(STORAGE_KEY, '1');
      (globalThis as unknown as { localStorage: unknown }).localStorage = ls;
      const { isUnlocked } = await loadComingSoon(false);
      expect(isUnlocked()).toBe(true);
    });

    it('is false (not thrown) when localStorage access throws', async () => {
      (globalThis as unknown as { localStorage: unknown }).localStorage = makeLocalStorage({ throwing: true });
      const { isUnlocked } = await loadComingSoon(false);
      expect(() => isUnlocked()).not.toThrow();
      expect(isUnlocked()).toBe(false);
    });
  });

  describe('tryUnlock', () => {
    it('unlocks and persists on a matching phrase', async () => {
      const ls = makeLocalStorage();
      (globalThis as unknown as { localStorage: unknown }).localStorage = ls;
      const { tryUnlock, isUnlocked } = await loadComingSoon(false);

      expect(tryUnlock(UNLOCK_PHRASE)).toBe(true);
      expect(ls._store.get(STORAGE_KEY)).toBe('1');
      expect(isUnlocked()).toBe(true);
    });

    it('matches case-insensitively and trims whitespace', async () => {
      (globalThis as unknown as { localStorage: unknown }).localStorage = makeLocalStorage();
      const { tryUnlock } = await loadComingSoon(false);
      expect(tryUnlock(`  ${UNLOCK_PHRASE.toUpperCase()}  `)).toBe(true);
    });

    it('rejects a wrong phrase and does not persist', async () => {
      const ls = makeLocalStorage();
      (globalThis as unknown as { localStorage: unknown }).localStorage = ls;
      const { tryUnlock } = await loadComingSoon(false);

      expect(tryUnlock('nope')).toBe(false);
      expect(ls._store.has(STORAGE_KEY)).toBe(false);
    });

    it('still reports success on a matching phrase even if persistence throws', async () => {
      (globalThis as unknown as { localStorage: unknown }).localStorage = makeLocalStorage({ throwing: true });
      const { tryUnlock } = await loadComingSoon(false);
      expect(() => tryUnlock(UNLOCK_PHRASE)).not.toThrow();
      expect(tryUnlock(UNLOCK_PHRASE)).toBe(true);
    });
  });

  describe('shouldGate', () => {
    it('is always false on native, regardless of unlock state', async () => {
      (globalThis as unknown as { localStorage: unknown }).localStorage = makeLocalStorage();
      const { shouldGate } = await loadComingSoon(true);
      expect(shouldGate()).toBe(false);
    });

    it('gates the web app when not unlocked', async () => {
      (globalThis as unknown as { localStorage: unknown }).localStorage = makeLocalStorage();
      (globalThis as unknown as { window: unknown }).window = { location: { search: '' } };
      const { shouldGate } = await loadComingSoon(false);
      expect(shouldGate()).toBe(true);
    });

    it('does not gate once the device is unlocked', async () => {
      const ls = makeLocalStorage();
      ls._store.set(STORAGE_KEY, '1');
      (globalThis as unknown as { localStorage: unknown }).localStorage = ls;
      (globalThis as unknown as { window: unknown }).window = { location: { search: '' } };
      const { shouldGate } = await loadComingSoon(false);
      expect(shouldGate()).toBe(false);
    });

    it('unlocks via a ?unlock=<phrase> query param and persists it', async () => {
      const ls = makeLocalStorage();
      (globalThis as unknown as { localStorage: unknown }).localStorage = ls;
      (globalThis as unknown as { window: unknown }).window = {
        location: { search: `?unlock=${encodeURIComponent(UNLOCK_PHRASE)}` },
      };
      const { shouldGate } = await loadComingSoon(false);
      expect(shouldGate()).toBe(false);
      expect(ls._store.get(STORAGE_KEY)).toBe('1');
    });

    it('ignores a wrong ?unlock= param and still gates', async () => {
      (globalThis as unknown as { localStorage: unknown }).localStorage = makeLocalStorage();
      (globalThis as unknown as { window: unknown }).window = { location: { search: '?unlock=wrong' } };
      const { shouldGate } = await loadComingSoon(false);
      expect(shouldGate()).toBe(true);
    });

    it('falls through to stored state when window is unavailable', async () => {
      const ls = makeLocalStorage();
      ls._store.set(STORAGE_KEY, '1');
      (globalThis as unknown as { localStorage: unknown }).localStorage = ls;
      delete (globalThis as { window?: unknown }).window;
      const { shouldGate } = await loadComingSoon(false);
      expect(() => shouldGate()).not.toThrow();
      expect(shouldGate()).toBe(false);
    });
  });
});
