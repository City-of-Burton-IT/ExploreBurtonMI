// Android App Links (#55): when a shared explore.burtonmi.gov link opens the
// installed app, route it to the matching in-app view/place. The app is
// hash-routed (#finances, #guide/<id>, #map/place/<id>), so the meaningful part
// of a deep link is its fragment; applying it to window.location.hash reuses the
// existing hashchange routing in App.svelte (view + place reconcile).
//
// Pairs with the place permalinks shipped in #47. Native only -- initDeepLinks is
// called behind Capacitor.isNativePlatform() from main.ts.

import { setView, clearSelection } from './store.svelte';

const SITE_HOST = 'explore.burtonmi.gov';

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

/** Wire the appUrlOpen listener. Native only. */
export async function initDeepLinks(): Promise<void> {
  const { App } = await import('@capacitor/app');
  await App.addListener('appUrlOpen', ({ url }) => {
    const route = routeFromUrl(url);
    if (route === null) return; // not our site -> let the OS handle it
    if (route) {
      // A view / guide-section / place-permalink fragment: let the existing
      // hashchange handler apply it (syncViewFromHash + reconcilePlace).
      window.location.hash = route;
    } else {
      // Bare site root -> the map, with any stale place selection cleared.
      clearSelection();
      setView('map');
    }
  });
}
