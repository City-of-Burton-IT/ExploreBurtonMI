// Android App Links (#55) + launcher shortcuts (#56): when a shared
// explore.burtonmi.gov link, or a long-press launcher shortcut, opens the app,
// route it to the matching in-app view/place. The app is hash-routed (#finances,
// #guide/<id>, #map/place/<id>), so the meaningful part of a deep link is its
// fragment; applying it to window.location.hash reuses the existing hashchange
// routing in App.svelte (view + place reconcile).
//
// Pairs with the place permalinks shipped in #47. Native only -- initDeepLinks is
// called behind Capacitor.isNativePlatform() from main.ts.

import { setView, clearSelection, requestNearMe } from './store.svelte';
import { SITE_BASE } from './hash';

const SITE_HOST = new URL(SITE_BASE).hostname;

/** A pseudo-route the "Near me" launcher shortcut (#56) carries; not a real view,
 *  it triggers geolocation instead of a hash change. */
export const NEAR_ME_ROUTE = 'near';

/** The in-app hash route (without the leading '#') for a deep-link URL:
 *  - a fragment like `#finances` -> `finances`
 *  - the site root (no fragment) -> `''` (the map)
 *  - any other host / unparseable URL -> null (caller ignores it). */
export function routeFromUrl(url: string): string | null {
  try {
    const u = new URL(url);
    if (u.hostname !== SITE_HOST) return null;
    return u.hash.replace(/^#/, '');
  } catch {
    return null;
  }
}

/** Apply a deep-link / shortcut / push-tap URL to the app state. */
export function applyRoute(url: string): void {
  const route = routeFromUrl(url);
  if (route === null) return; // not our site -> let the OS handle it
  if (route === NEAR_ME_ROUTE) {
    requestNearMe(); // "Near me" shortcut -> map + geolocation
  } else if (route) {
    // A view / guide-section / place-permalink fragment: let the existing
    // hashchange handler apply it (syncViewFromHash + reconcilePlace).
    window.location.hash = route;
  } else {
    // Bare site root -> the map, with any stale place selection cleared.
    clearSelection();
    setView('map');
  }
}

/** Wire deep-link handling. Native only. Handles both the cold-start launch URL
 *  (a tapped link or launcher shortcut that started the app -- appUrlOpen does
 *  NOT fire for this) and links that arrive while the app is already running. */
export async function initDeepLinks(): Promise<void> {
  const { App } = await import('@capacitor/app');
  try {
    const launch = await App.getLaunchUrl();
    if (launch?.url) applyRoute(launch.url);
  } catch {
    /* no launch URL */
  }
  await App.addListener('appUrlOpen', ({ url }) => applyRoute(url));
}
