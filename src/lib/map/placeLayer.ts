import L from 'leaflet';
import type { AppConfig, PlaceCollection, PlaceFeature } from '../types';
import { bindClusterPreview, type PlaceMarker } from './clusterPreview';
import { isOnMapPlace, markerStyle, markerTooltipHtml } from './presentation';

type PlaceLayerConfig = Pick<AppConfig, 'categoryField' | 'categories' | 'map'>;

export interface PlaceLayerHandle {
  setVisible(ids: Iterable<string>): void;
  setSelected(id: string | null): void;
  focus(id: string): void;
  setSuppressed(suppressed: boolean): void;
  destroy(): void;
}

export function createPlaceLayer(
  map: L.Map,
  data: PlaceCollection,
  config: PlaceLayerConfig,
  onSelect: (feature: PlaceFeature) => void,
): PlaceLayerHandle {
  const cluster = L.markerClusterGroup({
    showCoverageOnHover: false,
    zoomToBoundsOnClick: false,
  });
  const markers = new Map<string, L.CircleMarker>();
  const features = new Map<string, PlaceFeature>();
  const markerClickHandlers = new Map<L.CircleMarker, () => void>();
  let visibleIds = new Set<string>();
  let selectedId: string | null = null;
  let suppressed = false;
  let destroyed = false;
  let focusGeneration = 0;
  let pendingFocusId: string | null = null;

  for (const feature of data.features) {
    if (!isOnMapPlace(feature) || markers.has(feature.id)) continue;
    const [lng, lat] = feature.geometry.coordinates;
    const marker = L.circleMarker([lat, lng], markerStyle(feature, config));
    const selectFeature = () => onSelect(feature);
    marker.bindTooltip(markerTooltipHtml(feature, config.map.previewAttribute));
    marker.on('click', selectFeature);
    (marker as PlaceMarker).feature = feature;
    markers.set(feature.id, marker);
    features.set(feature.id, feature);
    markerClickHandlers.set(marker, selectFeature);
  }

  map.addLayer(cluster);
  const disposeClusterPreview = bindClusterPreview(map, cluster, onSelect);

  function reconcileVisible(): void {
    cluster.clearLayers();
    const visibleMarkers: L.CircleMarker[] = [];
    for (const [id, marker] of markers) {
      if (visibleIds.has(id)) visibleMarkers.push(marker);
    }
    cluster.addLayers(visibleMarkers);
  }

  function focusVisibleMember(id: string): void {
    const marker = markers.get(id);
    if (!marker || !visibleIds.has(id) || !cluster.hasLayer(marker)) return;
    const generation = ++focusGeneration;
    cluster.zoomToShowLayer(marker, () => {
      if (
        destroyed ||
        suppressed ||
        generation !== focusGeneration ||
        !visibleIds.has(id) ||
        !cluster.hasLayer(marker)
      ) {
        return;
      }
      marker.bringToFront();
    });
  }

  return {
    setVisible(ids) {
      if (destroyed) return;
      visibleIds = new Set(ids);
      if (!suppressed) {
        ++focusGeneration;
        reconcileVisible();
      }
    },
    setSelected(id) {
      if (destroyed || id === selectedId) return;
      if (selectedId) {
        const oldMarker = markers.get(selectedId);
        const oldFeature = features.get(selectedId);
        if (oldMarker && oldFeature) oldMarker.setStyle(markerStyle(oldFeature, config));
      }
      const marker = id ? markers.get(id) : undefined;
      const feature = id ? features.get(id) : undefined;
      if (marker && feature) {
        marker.setStyle(markerStyle(feature, config, true));
        marker.bringToFront();
      }
      selectedId = id;
    },
    focus(id) {
      if (destroyed) return;
      if (suppressed) {
        pendingFocusId = id;
        return;
      }
      focusVisibleMember(id);
    },
    setSuppressed(nextSuppressed) {
      if (destroyed || nextSuppressed === suppressed) return;
      suppressed = nextSuppressed;
      if (suppressed) {
        ++focusGeneration;
        pendingFocusId = null;
        if (map.hasLayer(cluster)) map.removeLayer(cluster);
      } else {
        reconcileVisible();
        if (!map.hasLayer(cluster)) map.addLayer(cluster);
        const focusId = pendingFocusId;
        pendingFocusId = null;
        if (focusId) focusVisibleMember(focusId);
      }
    },
    destroy() {
      if (destroyed) return;
      destroyed = true;
      ++focusGeneration;
      pendingFocusId = null;
      disposeClusterPreview();
      for (const [marker, handler] of markerClickHandlers) {
        marker.closeTooltip().unbindTooltip();
        marker.off('click', handler);
      }
      markerClickHandlers.clear();
      cluster.clearLayers();
      if (map.hasLayer(cluster)) map.removeLayer(cluster);
      markers.clear();
      features.clear();
      visibleIds.clear();
      selectedId = null;
    },
  };
}

