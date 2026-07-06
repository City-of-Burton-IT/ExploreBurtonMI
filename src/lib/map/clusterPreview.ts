// Cluster preview (#map): peek at the places inside a cluster bubble.
import L from 'leaflet';
import type { PlaceFeature } from '../types';
import { select } from '../store.svelte';
import { clusterSummary, CLUSTER_PREVIEW_MAX } from '../cluster';
import { escapeHtml } from './html';

/** A map layer (our circle markers) carrying its source place feature, so a
 *  cluster preview can read the names inside. Typed as the common Layer base so
 *  it fits both the circleMarkers we create and getAllChildMarkers()'s Marker[]. */
export type PlaceMarker = L.Layer & { feature?: PlaceFeature };

// markercluster's cluster events carry the hovered/clicked cluster on `.layer`.
type ClusterEvent = L.LeafletEvent & { layer: L.MarkerCluster };

function clusterNames(c: L.MarkerCluster): string[] {
  return (c.getAllChildMarkers() as PlaceMarker[])
    .map((m) => m.feature?.properties?.name)
    .filter((n): n is string => typeof n === 'string');
}

export function bindClusterPreview(map: L.Map, group: L.MarkerClusterGroup): void {
  // Desktop hover: a quick tooltip with a few names + "+N more".
  group.on('clustermouseover', (e) => {
    const c = (e as ClusterEvent).layer;
    const { shown, more } = clusterSummary(clusterNames(c), 6);
    const list = shown.map((n) => `<li>${escapeHtml(n)}</li>`).join('');
    const extra = more ? `<p class="cp-more">+${more} more — tap to see</p>` : '';
    c.bindTooltip(
      `<div class="cluster-peek"><p class="cp-head">${c.getChildCount()} places here</p><ul>${list}</ul>${extra}</div>`,
      { direction: 'top', offset: [0, -6], className: 'cluster-tip' },
    ).openTooltip();
  });
  group.on('clustermouseout', (e) => (e as ClusterEvent).layer.closeTooltip());

  // Tap / click: a small bubble opens a popup listing its places (tap one to open
  // it); a big bubble zooms to drill in (the hover tooltip covers the glance there,
  // and a 100-name popup wouldn't be useful).
  group.on('clusterclick', (e) => {
    const c = (e as ClusterEvent).layer;
    if (c.getChildCount() > CLUSTER_PREVIEW_MAX) {
      map.fitBounds(c.getBounds(), { padding: [40, 40] });
    } else {
      openClusterPreview(map, c);
    }
  });
}

function openClusterPreview(map: L.Map, c: L.MarkerCluster): void {
  const feats = (c.getAllChildMarkers() as PlaceMarker[])
    .map((m) => m.feature)
    .filter((f): f is PlaceFeature => !!f)
    .sort((a, b) => String(a.properties.name).localeCompare(String(b.properties.name)));
  const el = L.DomUtil.create('div', 'cluster-preview');
  const head = L.DomUtil.create('p', 'cp-head', el);
  head.textContent = `${feats.length} places here`;
  const ul = L.DomUtil.create('ul', '', el);
  for (const f of feats) {
    const li = L.DomUtil.create('li', '', ul);
    const btn = L.DomUtil.create('button', '', li) as HTMLButtonElement;
    btn.type = 'button';
    btn.textContent = String(f.properties.name); // textContent => no XSS
    L.DomEvent.on(btn, 'click', (ev) => {
      L.DomEvent.stop(ev);
      map.closePopup();
      select(f); // opens the detail sheet + reveals it on the map
    });
  }
  c.bindPopup(el, { className: 'cluster-popup', maxHeight: 260 }).openPopup();
}
