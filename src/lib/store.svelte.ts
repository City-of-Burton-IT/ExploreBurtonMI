// Shared reactive app state (Svelte 5 runes in a .svelte.ts module).
// Keeps cross-component state (selection + facet selections) in one place so
// Map, List, and Facets stay in sync without prop-drilling.

import { Capacitor } from '@capacitor/core';
import type { PlaceFeature, AppView } from './types';
import type { Selections } from './filter';
import { placeIdFromHash, placeHash } from './hash';
import { SAVED_KEY, loadSaved, serializeSaved, toggleSaved } from './savedPlaces';
import { THEME_KEY, loadThemePref, resolveTheme, type ThemePref } from './theme';
import { viewFromHash, guideSectionFromHash, guideSectionHash } from './dashboards';

// Pure dashboard registry + hash-routing helpers now live in ./dashboards
// (rune-free, so they can be imported without pulling in Svelte). Re-exported
// here so existing component imports (`from './store.svelte'`) keep working.
export type { DashboardItem, DashboardGroup } from './dashboards';
export {
  DASHBOARD_GROUPS,
  DASHBOARDS,
  isDashboard,
  dashboardGroupLabel,
  adjacentDashboards,
  viewFromHash,
  guideSectionFromHash,
  guideAnchorFromHash,
  guideSectionHash,
  guideHashNeedsNormalization,
} from './dashboards';

function initialView(): AppView {
  return typeof window === 'undefined' ? 'map' : viewFromHash(window.location.hash);
}

function initialGuideSection(): string | null {
  return typeof window === 'undefined' ? null : guideSectionFromHash(window.location.hash);
}

function initialSaved(): Set<string> {
  if (typeof localStorage === 'undefined') return new Set();
  try {
    return loadSaved(localStorage.getItem(SAVED_KEY));
  } catch {
    return new Set();
  }
}

function initialTheme(): ThemePref {
  if (typeof localStorage === 'undefined') return 'light';
  try {
    return loadThemePref(localStorage.getItem(THEME_KEY));
  } catch {
    return 'light';
  }
}

export const ui = $state<{
  selected: PlaceFeature | null;
  selections: Selections;
  query: string;
  /** which pane is shown on narrow (phone/tablet) screens */
  mobileView: 'map' | 'list';
  /** whether the About dialog is open */
  aboutOpen: boolean;
  /** whether the Settings dialog (cog: appearance + notifications) is open */
  settingsOpen: boolean;
  /** top-level section: the map, an info panel, or the guide */
  view: AppView;
  /** active Resident Guide section id (null = the guide's first section) */
  guideSection: string | null;
  /** the user's location once they tap "Near me" (drives map centering + list sort) */
  userLocation: { lat: number; lng: number } | null;
  /** true once the browser signals the PWA can be installed (Android/desktop) */
  canInstall: boolean;
  /** false when the device is offline (drives the "showing saved info" badge) */
  online: boolean;
  /** bumped to ask the Map to run "Near me" (e.g. from the native quick-actions
   *  row). The Map watches it and triggers geolocation. */
  nearMeNonce: number;
  /** ids of saved/favorite places (per-device, localStorage; #62) */
  savedIds: Set<string>;
  /** when true, the map + list show only saved places */
  savedOnly: boolean;
  /** theme preference (#61): system follows the OS, light/dark are explicit */
  theme: ThemePref;
  /** "Suggest an edit" modal (#3): open state + the place being edited
   *  (null place while open = "add my business") */
  suggest: { open: boolean; place: PlaceFeature | null };
  /** "Report an issue" (#14): modal state + the pin the resident dropped.
   *  pinMode = the map is waiting for a tap to place the pin. */
  report: { open: boolean; pinMode: boolean; lat: number | null; lng: number | null };
  /** Foreground push (#64): an in-app banner shown when an FCM message arrives
   *  while the app is open (Android does not raise a tray notification then). */
  pushBanner: { title: string; body: string; url: string | null } | null;
}>({
  selected: null,
  selections: {},
  query: '',
  mobileView: 'map',
  aboutOpen: false,
  settingsOpen: false,
  view: initialView(),
  guideSection: initialGuideSection(),
  userLocation: null,
  canInstall: false,
  online: typeof navigator === 'undefined' ? true : navigator.onLine,
  nearMeNonce: 0,
  savedIds: initialSaved(),
  savedOnly: false,
  theme: initialTheme(),
  suggest: { open: false, place: null },
  report: { open: false, pinMode: false, lat: null, lng: null },
  pushBanner: null,
});

// --- Foreground push banner (#64) -------------------------------------------
/** Show the in-app push banner (called when an FCM message arrives in foreground). */
export function showPushBanner(p: { title: string; body: string; url: string | null }): void {
  ui.pushBanner = p;
}
/** Dismiss the in-app push banner. */
export function dismissPushBanner(): void {
  ui.pushBanner = null;
}

// --- Suggest an edit (#3) ---------------------------------------------------
/** Open the "Suggest an edit" form -- for a specific place, or null = add-new. */
export function openSuggest(place: PlaceFeature | null): void {
  ui.suggest.place = place;
  ui.suggest.open = true;
}

export function closeSuggest(): void {
  ui.suggest.open = false;
  ui.suggest.place = null;
}

// --- Report an issue (#14) --------------------------------------------------
export function openReport(): void {
  ui.report.open = true;
  ui.report.pinMode = false;
}

export function closeReport(): void {
  ui.report.open = false;
  ui.report.pinMode = false;
  ui.report.lat = null;
  ui.report.lng = null;
}

/** Hide the modal and let the next map tap place the pin. */
export function startReportPin(): void {
  ui.report.open = false;
  ui.report.pinMode = true;
}

/** Map tap while in pin mode: record the spot and bring the form back. */
export function setReportPin(lat: number, lng: number): void {
  ui.report.lat = lat;
  ui.report.lng = lng;
  ui.report.pinMode = false;
  ui.report.open = true;
}

// --- Theme (#61) -----------------------------------------------------------
/** Apply the current preference to <html data-theme>, resolving "system" against
 *  the OS. Light is the absence of the dark token layer. */
function applyResolvedTheme(): void {
  if (typeof document === 'undefined') return;
  const prefersDark =
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia('(prefers-color-scheme: dark)').matches
      : false;
  const resolved = resolveTheme(ui.theme, prefersDark);
  document.documentElement.dataset.theme = resolved;
  // Native edge-to-edge (#30): Capacitor 8's CORE SystemBars plugin owns the
  // window layout + safe-area insets. The legacy @capacitor/status-bar plugin's
  // setOverlaysWebView set DEPRECATED fullscreen window flags that corrupted the
  // bottom (navigation-bar) inset -- content ended up hidden under the nav
  // buttons. SystemBars.setStyle covers BOTH bars' icon contrast: our dark theme
  // wants light icons (Style "DARK" = light content), light theme the reverse.
  if (Capacitor.isNativePlatform()) {
    import('@capacitor/core')
      .then(({ SystemBars, SystemBarsStyle }) => {
        SystemBars.setStyle({
          style: resolved === 'dark' ? SystemBarsStyle.Dark : SystemBarsStyle.Light,
        }).catch(() => {});
      })
      .catch(() => {});
  }
}

/** Set + persist the theme preference and apply it. */
export function setTheme(pref: ThemePref): void {
  ui.theme = pref;
  try {
    localStorage.setItem(THEME_KEY, pref);
  } catch {
    /* storage unavailable -> session-only */
  }
  applyResolvedTheme();
}

/** Apply the saved theme on startup and keep "system" in sync with the OS. Call
 *  once, as early as possible (main.ts), to avoid a flash of the wrong theme. */
export function initTheme(): void {
  applyResolvedTheme();
  if (typeof window !== 'undefined' && window.matchMedia) {
    window
      .matchMedia('(prefers-color-scheme: dark)')
      .addEventListener('change', () => {
        if (ui.theme === 'system') applyResolvedTheme();
      });
  }
}

// --- Saved / favorite places (#62) -----------------------------------------
/** Whether a place id is currently saved. */
export function isSaved(id: string): boolean {
  return ui.savedIds.has(id);
}

/** Toggle a place's saved state and persist the set to localStorage. */
export function toggleSavedPlace(id: string): void {
  ui.savedIds = toggleSaved(ui.savedIds, id);
  try {
    localStorage.setItem(SAVED_KEY, serializeSaved(ui.savedIds));
  } catch {
    /* storage unavailable (private mode) -> keep it for this session only */
  }
  // Leaving the saved-only view empty would look broken; drop back to all places.
  if (ui.savedOnly && ui.savedIds.size === 0) ui.savedOnly = false;
}

/** Show only saved places (true) or all places (false). */
export function setSavedOnly(on: boolean): void {
  ui.savedOnly = on;
}

/** Ask the map to locate the user ("Near me") from anywhere -- e.g. the native
 *  quick-actions row. Switches to the map; the Map component does the geolocation. */
export function requestNearMe(): void {
  setView('map');
  ui.nearMeNonce += 1;
}

/** Watch the browser's online/offline events so the offline badge stays current.
 *  Call once (App onMount); returns a teardown fn. No-op without a window. */
export function initOnlineWatch(): () => void {
  if (typeof window === 'undefined') return () => {};
  const on = () => (ui.online = true);
  const off = () => (ui.online = false);
  window.addEventListener('online', on);
  window.addEventListener('offline', off);
  ui.online = navigator.onLine; // resync in case it changed before mount
  return () => {
    window.removeEventListener('online', on);
    window.removeEventListener('offline', off);
  };
}

/** Record (or clear) the user's location after a "Near me" request. */
export function setUserLocation(loc: { lat: number; lng: number } | null): void {
  ui.userLocation = loc;
}

// --- PWA install -----------------------------------------------------------
// The browser fires `beforeinstallprompt` (Android/desktop Chromium) once the app
// is installable; we stash it so an in-app button can trigger the native prompt on
// demand. iOS has no such event -- the component shows a manual hint instead.
export interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

let deferredInstallPrompt: BeforeInstallPromptEvent | null = null;

/** Called from main.ts when the browser offers an install. */
export function captureInstallPrompt(e: BeforeInstallPromptEvent): void {
  deferredInstallPrompt = e;
  ui.canInstall = true;
}

/** Fire the stored native install prompt (Android/desktop). */
export async function triggerInstall(): Promise<void> {
  if (!deferredInstallPrompt) return;
  await deferredInstallPrompt.prompt();
  await deferredInstallPrompt.userChoice;
  deferredInstallPrompt = null;
  ui.canInstall = false;
}

/** Called when the app has been installed (clears any install UI). */
export function markInstalled(): void {
  deferredInstallPrompt = null;
  ui.canInstall = false;
}

/** Switch the top-level view and reflect it in the URL hash (shareable + Back). */
export function setView(view: AppView): void {
  ui.view = view;
  if (typeof window === 'undefined') return;
  if (view === 'map') {
    if (window.location.hash) {
      history.pushState(null, '', window.location.pathname + window.location.search);
    }
  } else if (viewFromHash(window.location.hash) !== view) {
    window.location.hash = view;
  }
}

/** Select a Resident Guide section and reflect it in the hash (#guide/<id>). */
export function setGuideSection(id: string): void {
  ui.view = 'guide';
  ui.guideSection = id;
  if (typeof window !== 'undefined') window.location.hash = guideSectionHash(id);
}

/** Normalize an invalid guide deep link without adding another history entry. */
export function replaceGuideSection(id: string): void {
  ui.view = 'guide';
  ui.guideSection = id;
  if (typeof window === 'undefined') return;
  history.replaceState(
    null,
    '',
    `${window.location.pathname}${window.location.search}#${guideSectionHash(id)}`,
  );
}

/** Sync the view (+ guide section) from the current hash (Back/Forward + deep links). */
export function syncViewFromHash(): void {
  const hash = typeof window === 'undefined' ? '' : window.location.hash;
  ui.view = viewFromHash(hash);
  ui.guideSection = guideSectionFromHash(hash);
}

export function setMobileView(view: 'map' | 'list'): void {
  ui.mobileView = view;
}

// --- Overlay registry (for the native hardware back button) ----------------
// Modals that own their open-state locally (Lightbox, WelcomeModal) register a
// close handler here while open so the Android back button can dismiss the
// top-most one before changing view. Store-driven overlays (About, Detail) are
// read directly from `ui` instead -- see lib/nativeBack.ts. Read imperatively on
// a back press, so no reactivity is needed here.
const overlayClosers: Array<() => void> = [];

/** Register a close handler while a local-state overlay is open; returns an
 *  unregister fn (call it on close / component teardown). */
export function registerOverlay(close: () => void): () => void {
  overlayClosers.push(close);
  return () => {
    const i = overlayClosers.lastIndexOf(close);
    if (i >= 0) overlayClosers.splice(i, 1);
  };
}

/** True when a locally-owned overlay (lightbox/welcome) is open. */
export function hasOverlay(): boolean {
  return overlayClosers.length > 0;
}

/** Close the most-recently-registered open overlay. */
export function closeTopOverlay(): void {
  overlayClosers[overlayClosers.length - 1]?.();
}

export function openAbout(): void {
  ui.aboutOpen = true;
}

export function closeAbout(): void {
  ui.aboutOpen = false;
}

export function openSettings(): void {
  ui.settingsOpen = true;
}

export function closeSettings(): void {
  ui.settingsOpen = false;
}

export function select(feature: PlaceFeature | null): void {
  ui.selected = feature;
  if (feature) {
    // Picking a place reveals it on the map (+ its detail sheet) and makes the
    // URL a shareable permalink (#map/place/<id>). The id-equality guard means
    // applying a place from the hash re-writes the same value -> no event loop.
    ui.mobileView = 'map';
    ui.view = 'map';
    if (typeof window !== 'undefined') {
      const h = placeHash(feature.id);
      if (window.location.hash.replace(/^#/, '') !== h) window.location.hash = h;
    }
  }
}

export function clearSelection(): void {
  ui.selected = null;
  // Drop the place from the URL (keep the clean map URL) without a history entry.
  if (typeof window !== 'undefined' && placeIdFromHash(window.location.hash)) {
    history.replaceState(null, '', window.location.pathname + window.location.search);
  }
}

/** Add or remove a value from a facet field's selection. */
export function toggleFacet(field: string, value: string): void {
  const current = ui.selections[field] ?? [];
  const next = current.includes(value)
    ? current.filter((v) => v !== value)
    : [...current, value];
  ui.selections = { ...ui.selections, [field]: next };
}

/** Clear all selected values for one facet field. */
export function clearFacet(field: string): void {
  ui.selections = { ...ui.selections, [field]: [] };
}
