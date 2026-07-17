import { dataFetch } from '../remote';
import type { InfoPanel, InfoSummary } from './infoPanel';
import {
  validateFreshnessMap,
  validateInfoPanel,
  validateSummaryMap,
} from './infoPanel';

export type DashboardErrorKind = 'missing' | 'http' | 'network' | 'validation';

export interface DashboardLoadError {
  kind: DashboardErrorKind;
  message: string;
}

export interface DashboardState {
  panel: InfoPanel | null;
  loading: boolean;
  error: DashboardLoadError | null;
  requested: boolean;
}

export interface DashboardData {
  state(id: string): DashboardState;
  load(id: string): Promise<InfoPanel | null>;
  retry(id: string): Promise<InfoPanel | null>;
  loadAll(): Promise<void>;
  readonly panels: Record<string, InfoPanel | null>;
  readonly allLoading: boolean;
  readonly allLoaded: boolean;
}

interface DashboardDataOptions {
  fetch?: (url: string) => Promise<Response>;
  isOnline?: () => boolean;
  prefetchAdjacent?: boolean;
}

interface DashboardMetadata {
  summaries: Record<string, InfoSummary>;
  freshness: Record<string, string>;
}

class LoadFailure extends Error {
  constructor(readonly kind: DashboardErrorKind, message: string) {
    super(message);
  }
}

function loadError(error: unknown): DashboardLoadError {
  if (error instanceof LoadFailure) return { kind: error.kind, message: error.message };
  return {
    kind: 'validation',
    message: error instanceof Error ? error.message : String(error),
  };
}

/**
 * Create the session-scoped dashboard cache. Construction has no network side
 * effects; a route must explicitly call load(), retry(), or loadAll().
 */
export function createDashboardData(
  dashboardIds: readonly string[],
  options: DashboardDataOptions = {},
): DashboardData {
  const ids = [...dashboardIds];
  const knownIds = new Set(ids);
  if (knownIds.size !== ids.length) throw new Error('Dashboard ids must be unique');

  const fetcher = options.fetch ?? dataFetch;
  const isOnline = options.isOnline ?? (() => typeof navigator === 'undefined' || navigator.onLine);
  const prefetchAdjacent = options.prefetchAdjacent ?? true;
  const states = $state(
    Object.fromEntries(
      ids.map((id) => [id, { panel: null, loading: false, error: null, requested: false }]),
    ) as Record<string, DashboardState>,
  );
  let allLoading = $state(false);
  const inFlight = new Map<string, Promise<InfoPanel | null>>();
  let metadataPromise: Promise<DashboardMetadata> | null = null;

  function state(id: string): DashboardState {
    if (!knownIds.has(id)) throw new Error(`Unknown dashboard id: ${id}`);
    return states[id];
  }

  async function loadOverlay<T>(
    url: string,
    validate: (value: unknown, ids: readonly string[]) => T,
  ): Promise<T | Record<string, never>> {
    let response: Response;
    try {
      response = await fetcher(url);
    } catch {
      return {};
    }
    if (!response.ok) return {};
    const raw = await response.json();
    return validate(raw, ids);
  }

  function metadata(): Promise<DashboardMetadata> {
    if (metadataPromise) return metadataPromise;
    metadataPromise = Promise.all([
      loadOverlay('summaries.json', validateSummaryMap),
      loadOverlay('freshness.json', validateFreshnessMap),
    ])
      .then(([summaries, freshness]) => ({
        summaries: summaries as Record<string, InfoSummary>,
        freshness: freshness as Record<string, string>,
      }))
      .catch((error) => {
        metadataPromise = null;
        throw error;
      });
    return metadataPromise;
  }

  async function fetchPanel(id: string): Promise<InfoPanel> {
    let response: Response;
    try {
      response = await fetcher(`info-${id}.json`);
    } catch (error) {
      throw new LoadFailure(
        'network',
        error instanceof Error ? error.message : `Network error loading dashboard ${id}`,
      );
    }
    if (!response.ok) {
      const kind: DashboardErrorKind = response.status === 404 || response.status === 410
        ? 'missing'
        : 'http';
      throw new LoadFailure(kind, `Dashboard ${id} returned HTTP ${response.status}`);
    }

    let raw: unknown;
    try {
      raw = await response.json();
      return validateInfoPanel(raw, id);
    } catch (error) {
      throw new LoadFailure(
        'validation',
        error instanceof Error ? error.message : `Invalid dashboard ${id}`,
      );
    }
  }

  async function performLoad(id: string, allowPrefetch: boolean): Promise<InfoPanel | null> {
    const current = state(id);
    current.requested = true;
    current.loading = true;
    current.error = null;

    try {
      const [basePanel, overlays] = await Promise.all([fetchPanel(id), metadata()]);
      const panel: InfoPanel = {
        ...basePanel,
        summary: basePanel.summary ?? overlays.summaries[id],
        lastUpdated: basePanel.lastUpdated ?? overlays.freshness[id],
      };
      current.panel = panel;

      if (allowPrefetch && prefetchAdjacent && isOnline()) {
        const nextId = ids[ids.indexOf(id) + 1];
        if (nextId) void loadInternal(nextId, false);
      }
      return panel;
    } catch (error) {
      current.panel = null;
      current.error = loadError(error);
      return null;
    } finally {
      current.loading = false;
    }
  }

  function loadInternal(id: string, allowPrefetch: boolean): Promise<InfoPanel | null> {
    const current = state(id);
    if (current.panel && !current.error) return Promise.resolve(current.panel);

    const pending = inFlight.get(id);
    if (pending) return pending;

    let request!: Promise<InfoPanel | null>;
    request = performLoad(id, allowPrefetch).finally(() => {
      if (inFlight.get(id) === request) inFlight.delete(id);
    });
    inFlight.set(id, request);
    return request;
  }

  async function loadAll(): Promise<void> {
    allLoading = true;
    try {
      await Promise.all(ids.map((id) => loadInternal(id, false)));
    } finally {
      allLoading = false;
    }
  }

  return {
    state,
    load: (id) => loadInternal(id, true),
    retry: (id) => {
      const current = state(id);
      current.panel = null;
      current.error = null;
      return loadInternal(id, true);
    },
    loadAll,
    get panels() {
      return Object.fromEntries(ids.map((id) => [id, states[id].panel]));
    },
    get allLoading() {
      return allLoading;
    },
    get allLoaded() {
      return ids.every((id) => states[id].requested && !states[id].loading);
    },
  };
}
