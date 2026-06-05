// Shared reactive app state (Svelte 5 runes in a .svelte.ts module).
// Keeps cross-component state (selection + facet selections) in one place so
// Map, List, and Facets stay in sync without prop-drilling.

import type { PlaceFeature, AppView } from './types';
import type { Selections } from './filter';

/** Map a URL hash (#finances) to a top-level view; anything else is the map. */
export function viewFromHash(hash: string): AppView {
  const key = hash.replace(/^#/, '');
  return key === 'finances' || key === 'demographics' ? key : 'map';
}

function initialView(): AppView {
  return typeof window === 'undefined' ? 'map' : viewFromHash(window.location.hash);
}

export const ui = $state<{
  selected: PlaceFeature | null;
  selections: Selections;
  query: string;
  /** which pane is shown on narrow (phone/tablet) screens */
  mobileView: 'map' | 'list';
  /** whether the About dialog is open */
  aboutOpen: boolean;
  /** top-level section: the map, or an info panel */
  view: AppView;
}>({
  selected: null,
  selections: {},
  query: '',
  mobileView: 'map',
  aboutOpen: false,
  view: initialView(),
});

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

/** Sync the view from the current hash (Back/Forward + deep links). */
export function syncViewFromHash(): void {
  ui.view = typeof window === 'undefined' ? 'map' : viewFromHash(window.location.hash);
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
