import { describe, expect, it, vi } from 'vitest';
import { createReportPinModeAdapter } from '../src/lib/map/reportPinMode';

function suppressionHandle() {
  return { setSuppressed: vi.fn() };
}

describe('createReportPinModeAdapter', () => {
  it('synchronizes suppression, cursor, popups, and instructions as one transition', () => {
    const map = { closePopup: vi.fn() };
    const mapElement = { style: { cursor: 'grab' } };
    const baseMap = { setOverlaySuppressed: vi.fn() };
    const placeLayer = suppressionHandle();
    const closureLayer = suppressionHandle();
    const onInstructions = vi.fn();
    const adapter = createReportPinModeAdapter({
      map: map as never,
      mapElement: mapElement as never,
      getBaseMap: () => baseMap,
      getPlaceLayer: () => placeLayer,
      getClosureLayer: () => closureLayer,
      onInstructions,
    });

    adapter.synchronize(true);

    expect(placeLayer.setSuppressed).toHaveBeenCalledWith(true);
    expect(closureLayer.setSuppressed).toHaveBeenCalledWith(true);
    expect(baseMap.setOverlaySuppressed).toHaveBeenCalledWith(true);
    expect(map.closePopup).toHaveBeenCalledOnce();
    expect(mapElement.style.cursor).toBe('crosshair');
    expect(onInstructions).toHaveBeenCalledWith(true);

    adapter.synchronize(false);

    expect(placeLayer.setSuppressed).toHaveBeenLastCalledWith(false);
    expect(closureLayer.setSuppressed).toHaveBeenLastCalledWith(false);
    expect(baseMap.setOverlaySuppressed).toHaveBeenLastCalledWith(false);
    expect(mapElement.style.cursor).toBe('grab');
    expect(onInstructions).toHaveBeenLastCalledWith(false);
  });

  it('restores the latest handles and tears down idempotently', () => {
    const mapElement = { style: { cursor: '' } };
    const originalPlace = suppressionHandle();
    const latestPlace = suppressionHandle();
    const originalClosure = suppressionHandle();
    const latestClosure = suppressionHandle();
    const originalBase = { setOverlaySuppressed: vi.fn() };
    const latestBase = { setOverlaySuppressed: vi.fn() };
    let placeLayer = originalPlace;
    let closureLayer = originalClosure;
    let baseMap = originalBase;
    const onInstructions = vi.fn();
    const adapter = createReportPinModeAdapter({
      map: { closePopup: vi.fn() } as never,
      mapElement: mapElement as never,
      getBaseMap: () => baseMap,
      getPlaceLayer: () => placeLayer,
      getClosureLayer: () => closureLayer,
      onInstructions,
    });

    adapter.synchronize(true);
    placeLayer = latestPlace;
    closureLayer = latestClosure;
    baseMap = latestBase;
    adapter.destroy();
    adapter.destroy();

    expect(originalPlace.setSuppressed).toHaveBeenCalledTimes(1);
    expect(originalClosure.setSuppressed).toHaveBeenCalledTimes(1);
    expect(originalBase.setOverlaySuppressed).toHaveBeenCalledTimes(1);
    expect(latestPlace.setSuppressed).toHaveBeenCalledOnce();
    expect(latestPlace.setSuppressed).toHaveBeenCalledWith(false);
    expect(latestClosure.setSuppressed).toHaveBeenCalledOnce();
    expect(latestClosure.setSuppressed).toHaveBeenCalledWith(false);
    expect(latestBase.setOverlaySuppressed).toHaveBeenCalledOnce();
    expect(latestBase.setOverlaySuppressed).toHaveBeenCalledWith(false);
    expect(mapElement.style.cursor).toBe('');
    expect(onInstructions.mock.calls).toEqual([[true], [false]]);

    adapter.synchronize(true);
    expect(latestPlace.setSuppressed).toHaveBeenCalledTimes(1);
  });
});

