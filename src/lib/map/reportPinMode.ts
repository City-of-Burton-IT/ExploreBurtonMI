import type L from 'leaflet';
import type { BaseMapHandle } from './createBaseMap';
import type { ClosureLayerHandle } from './closureLayer';
import type { PlaceLayerHandle } from './placeLayer';

export interface ReportPinModeAdapter {
  synchronize(enabled: boolean): void;
  destroy(): void;
}

export interface ReportPinModeTargets {
  map: Pick<L.Map, 'closePopup'>;
  mapElement: Pick<HTMLElement, 'style'>;
  getBaseMap: () => Pick<BaseMapHandle, 'setOverlaySuppressed'> | undefined;
  getPlaceLayer: () => Pick<PlaceLayerHandle, 'setSuppressed'> | undefined;
  getClosureLayer: () => Pick<ClosureLayerHandle, 'setSuppressed'> | undefined;
  onInstructions: (visible: boolean) => void;
}

export function createReportPinModeAdapter(
  targets: ReportPinModeTargets,
): ReportPinModeAdapter {
  let active = false;
  let destroyed = false;
  let previousCursor = '';

  function apply(enabled: boolean): void {
    const wasActive = active;
    if (enabled && !wasActive) previousCursor = targets.mapElement.style.cursor;

    targets.getPlaceLayer()?.setSuppressed(enabled);
    targets.getClosureLayer()?.setSuppressed(enabled);
    targets.getBaseMap()?.setOverlaySuppressed(enabled);
    if (enabled) targets.map.closePopup();

    if (enabled) targets.mapElement.style.cursor = 'crosshair';
    else if (wasActive) targets.mapElement.style.cursor = previousCursor;
    targets.onInstructions(enabled);
    active = enabled;
  }

  return {
    synchronize(enabled) {
      if (destroyed) return;
      apply(enabled);
    },
    destroy() {
      if (destroyed) return;
      if (active) apply(false);
      destroyed = true;
    },
  };
}

