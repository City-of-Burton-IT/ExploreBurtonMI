// Cluster preview (#map): peek at the places inside a cluster bubble.
import L from 'leaflet';
import type { PlaceFeature } from '../types';
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

export function bindClusterPreview(
  map: L.Map,
  group: L.MarkerClusterGroup,
  onSelect: (feature: PlaceFeature) => void,
): () => void {
  const tooltipClusters = new Set<L.MarkerCluster>();
  const popupClusters = new Set<L.MarkerCluster>();
  const popupButtons = new Map<HTMLElement, L.DomEvent.EventHandlerFn>();
  let disposed = false;

  function clearPopupButtonListeners(): void {
    for (const [button, handler] of popupButtons) L.DomEvent.off(button, 'click', handler);
    popupButtons.clear();
  }

  // Desktop hover: a quick tooltip with a few names + "+N more".
  const handleMouseOver = (e: L.LeafletEvent) => {
    const c = (e as ClusterEvent).layer;
    tooltipClusters.add(c);
    const { shown, more } = clusterSummary(clusterNames(c), 6);
    const list = shown.map((n) => `<li>${escapeHtml(n)}</li>`).join('');
    const extra = more ? `<p class="cp-more">+${more} more — tap to see</p>` : '';
    c.bindTooltip(
      `<div class="cluster-peek"><p class="cp-head">${c.getChildCount()} places here</p><ul>${list}</ul>${extra}</div>`,
      { direction: 'top', offset: [0, -6], className: 'cluster-tip' },
    ).openTooltip();
  };
  const handleMouseOut = (e: L.LeafletEvent) => (e as ClusterEvent).layer.closeTooltip();

  // Tap / click: a small bubble opens a popup listing its places (tap one to open
  // it); a big bubble zooms to drill in (the hover tooltip covers the glance there,
  // and a 100-name popup wouldn't be useful).
  const handleClick = (e: L.LeafletEvent) => {
    const c = (e as ClusterEvent).layer;
    if (c.getChildCount() > CLUSTER_PREVIEW_MAX) {
      map.fitBounds(c.getBounds(), { padding: [40, 40] });
    } else {
      clearPopupButtonListeners();
      popupClusters.add(c);
      openClusterPreview(map, c, onSelect, popupButtons);
    }
  };

  group.on('clustermouseover', handleMouseOver);
  group.on('clustermouseout', handleMouseOut);
  group.on('clusterclick', handleClick);

  return () => {
    if (disposed) return;
    disposed = true;
    group.off('clustermouseover', handleMouseOver);
    group.off('clustermouseout', handleMouseOut);
    group.off('clusterclick', handleClick);
    clearPopupButtonListeners();
    for (const cluster of tooltipClusters) cluster.closeTooltip().unbindTooltip();
    for (const cluster of popupClusters) cluster.closePopup().unbindPopup();
    if (popupClusters.size > 0) map.closePopup();
    tooltipClusters.clear();
    popupClusters.clear();
  };
}

function openClusterPreview(
  map: L.Map,
  c: L.MarkerCluster,
  onSelect: (feature: PlaceFeature) => void,
  popupButtons: Map<HTMLElement, L.DomEvent.EventHandlerFn>,
): void {
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
    const handleSelect: L.DomEvent.EventHandlerFn = (ev) => {
      L.DomEvent.stop(ev);
      map.closePopup();
      onSelect(f);
    };
    popupButtons.set(btn, handleSelect);
    L.DomEvent.on(btn, 'click', handleSelect);
  }
  c.bindPopup(el, { className: 'cluster-popup', maxHeight: 260 }).openPopup();
}

