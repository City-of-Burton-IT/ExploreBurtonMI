import { Capacitor } from '@capacitor/core';

// HYBRID DATA LOADING
// ===================
// In the native app the web assets (HTML/JS/CSS) are bundled and frozen at build
// time, but the DATA files (the geojson layers + dashboard json) change often on the
// website. So when running natively we fetch those from the live site FIRST -- so a
// push to `main` updates the data on phones with no app release -- and fall back to
// the copy bundled inside the app when the network is unavailable (offline-friendly).
//
// On the web this is a no-op: the site already IS this origin, so we just fetch the
// same relative path as before. Code/feature changes still require a new app release;
// only data rides the live channel.
const REMOTE_BASE = 'https://explore.burtonmi.gov/';
const REMOTE_TIMEOUT_MS = 5000;

const isNative = Capacitor.isNativePlatform();

const isAbsolute = (path: string): boolean => /^https?:\/\//i.test(path);

/**
 * Fetch a bundled data file.
 *
 * Natively: try the live site (so data updates reach phones without an app release),
 * then fall back to the bundled copy on any network failure or non-OK response.
 * On the web (or for absolute URLs like third-party APIs): a plain fetch, unchanged.
 */
export async function dataFetch(path: string): Promise<Response> {
  if (!isNative || isAbsolute(path)) {
    return fetch(path);
  }
  const remoteUrl = REMOTE_BASE + path.replace(/^\.?\//, '');
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REMOTE_TIMEOUT_MS);
    const res = await fetch(remoteUrl, { signal: controller.signal });
    clearTimeout(timer);
    if (res.ok) return res;
    // Reachable but missing/errored on the server -> fall back to the bundled copy.
  } catch {
    // Offline or timed out -> fall back to the bundled copy.
  }
  return fetch(path);
}
