// Shared reactive app state (Svelte 5 runes in a .svelte.ts module).
// Keeps cross-component state (selection + facet selections) in one place so
// Map, List, and Facets stay in sync without prop-drilling.

import type { PlaceFeature, AppView, InfoView } from './types';
import type { Selections } from './filter';

export interface DashboardItem {
  id: InfoView;
  label: string;
}
export interface DashboardGroup {
  label: string;
  items: DashboardItem[];
}

/** Dashboards organized into themed groups -- the single source of truth for the
 *  grouped menu, hash routing, and which panels to load. Add a dashboard by
 *  placing it in the right group; everything else derives from this. */
export const DASHBOARD_GROUPS: DashboardGroup[] = [
  {
    label: 'People & Housing',
    items: [
      { id: 'demographics', label: 'Demographics' },
      { id: 'housing', label: 'Housing & Growth' },
      { id: 'zoning', label: 'Zoning' },
      { id: 'schools', label: 'Schools' },
    ],
  },
  {
    label: 'Money & Jobs',
    items: [
      { id: 'finances', label: 'Finances' },
      { id: 'jobs', label: 'Jobs & Employers' },
    ],
  },
  {
    label: 'Health & Environment',
    items: [
      { id: 'health', label: 'Community Health' },
      { id: 'water', label: 'Drinking Water' },
      { id: 'environment', label: 'Environment' },
    ],
  },
  {
    label: 'Infrastructure',
    items: [
      { id: 'broadband', label: 'Broadband Access' },
      { id: 'bridges', label: 'Bridges & Infrastructure' },
      { id: 'roads', label: 'Roads & Pavement' },
      { id: 'trails', label: 'Trails & Pathways' },
    ],
  },
];

/** Flat list (display order) derived from the groups -- used by hash routing,
 *  panel loading, and the active-dashboard lookup. */
export const DASHBOARDS: DashboardItem[] = DASHBOARD_GROUPS.flatMap((g) => g.items);

const DASHBOARD_IDS = new Set<string>(DASHBOARDS.map((d) => d.id));

/** True when a view is one of the dashboard info-panels. */
export function isDashboard(view: AppView): view is InfoView {
  return DASHBOARD_IDS.has(view);
}

/** Map a URL hash (#finances, #guide, #guide/trash) to a top-level view. */
export function viewFromHash(hash: string): AppView {
  const key = hash.replace(/^#/, '').split('/')[0];
  if (key === 'guide' || DASHBOARD_IDS.has(key)) return key as AppView;
  return 'map';
}

/** The guide section id from a `#guide/<id>` hash, or null. */
export function guideSectionFromHash(hash: string): string | null {
  const parts = hash.replace(/^#/, '').split('/');
  return parts[0] === 'guide' && parts[1] ? parts[1] : null;
}

function initialView(): AppView {
  return typeof window === 'undefined' ? 'map' : viewFromHash(window.location.hash);
}

function initialGuideSection(): string | null {
  return typeof window === 'undefined' ? null : guideSectionFromHash(window.location.hash);
}

export const ui = $state<{
  selected: PlaceFeature | null;
  selections: Selections;
  query: string;
  /** which pane is shown on narrow (phone/tablet) screens */
  mobileView: 'map' | 'list';
  /** whether the About dialog is open */
  aboutOpen: boolean;
  /** top-level section: the map, an info panel, or the guide */
  view: AppView;
  /** active Resident Guide section id (null = the guide's first section) */
  guideSection: string | null;
  /** the user's location once they tap "Near me" (drives map centering + list sort) */
  userLocation: { lat: number; lng: number } | null;
  /** true once the browser signals the PWA can be installed (Android/desktop) */
  canInstall: boolean;
}>({
  selected: null,
  selections: {},
  query: '',
  mobileView: 'map',
  aboutOpen: false,
  view: initialView(),
  guideSection: initialGuideSection(),
  userLocation: null,
  canInstall: false,
});

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
  if (typeof window !== 'undefined') window.location.hash = `guide/${id}`;
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

export function openAbout(): void {
  ui.aboutOpen = true;
}

export function closeAbout(): void {
  ui.aboutOpen = false;
}

export function select(feature: PlaceFeature | null): void {
  ui.selected = feature;
  // Picking a place from the list should reveal it on the map (+ its detail sheet).
  if (feature) ui.mobileView = 'map';
}

export function clearSelection(): void {
  ui.selected = null;
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
