// Android hardware back-button handling (Capacitor native only).
//
// Registering a `backButton` listener on @capacitor/app OVERRIDES the WebView
// default entirely, so we own every case -- including exit. The priority chain:
//   1. a locally-owned overlay is open (lightbox / welcome) -> close the top one
//   2. the About dialog is open                              -> close it
//   3. a place Detail sheet is open                          -> clear selection
//   4. we're on a non-map view (dashboard / guide)           -> return to the map
//   5. otherwise                                             -> exit the app
//
// So: from a dashboard, Back -> map, a second Back -> exit; an open sheet/dialog
// closes before the view changes. Web/PWA is untouched (initNativeBack is only
// called behind Capacitor.isNativePlatform()).

import type { AppView } from './types';
import { ui, closeAbout, clearSelection, setView, hasOverlay, closeTopOverlay } from './store.svelte';

export type BackStep = 'overlay' | 'about' | 'detail' | 'go-map' | 'exit';

/** Pure decision: which back action to take given the current UI state. */
export function backDecision(s: {
  overlay: boolean;
  about: boolean;
  detail: boolean;
  view: AppView;
}): BackStep {
  if (s.overlay) return 'overlay';
  if (s.about) return 'about';
  if (s.detail) return 'detail';
  if (s.view !== 'map') return 'go-map';
  return 'exit';
}

/** Run one back press against the live store. `exit` is delegated to the caller
 *  (the native listener calls App.exitApp) so this stays import-light + testable. */
export function performBack(exit: () => void): void {
  const step = backDecision({
    overlay: hasOverlay(),
    about: ui.aboutOpen,
    detail: !!ui.selected,
    view: ui.view,
  });
  switch (step) {
    case 'overlay':
      closeTopOverlay();
      break;
    case 'about':
      closeAbout();
      break;
    case 'detail':
      clearSelection();
      break;
    case 'go-map':
      setView('map');
      break;
    case 'exit':
      exit();
      break;
  }
}

/** Wire the Android hardware back button. Native only -- import dynamically from
 *  main.ts behind a Capacitor.isNativePlatform() guard. */
export async function initNativeBack(): Promise<void> {
  const { App } = await import('@capacitor/app');
  await App.addListener('backButton', () => {
    performBack(() => {
      App.exitApp();
    });
  });
}
