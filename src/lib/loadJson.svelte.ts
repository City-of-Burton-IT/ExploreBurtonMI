// One-shot reactive data loading for view components: kick off the fetch at
// component init and expose { loading, data } runes, replacing the repeated
// onMount + try/catch + loading-flag block.
import { dataFetch } from './remote';

export interface AsyncLoad<T> {
  /** true until the loader settles (resolve or throw) */
  readonly loading: boolean;
  /** the loader's result; `fallback` until it resolves and whenever it throws */
  readonly data: T;
}

/** Run an async loader once, exposing its progress/result reactively. */
export function loadAsync<T>(load: () => Promise<T>, fallback: T): AsyncLoad<T> {
  let loading = $state(true);
  let data = $state(fallback) as T;
  (async () => {
    try {
      data = await load();
    } catch {
      data = fallback;
    }
    loading = false;
  })();
  return {
    get loading() {
      return loading;
    },
    get data() {
      return data;
    },
  };
}

/** Fetch one of the site's JSON data files (via dataFetch, so the remote data
 *  root and SW cache apply) and map/validate the raw payload. A non-OK response
 *  or a throwing mapper (e.g. a bundle validator) yields `fallback`. */
export function loadJson<T>(
  source: string,
  map: (raw: unknown) => T,
  fallback: T,
): AsyncLoad<T> {
  return loadAsync(async () => {
    const r = await dataFetch(source);
    return r.ok ? map(await r.json()) : fallback;
  }, fallback);
}
