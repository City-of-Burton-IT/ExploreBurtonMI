import { beforeEach, describe, expect, it, vi } from 'vitest';

let nativePlatform = false;
const requestPermissions = vi.fn();
const getCurrentPosition = vi.fn();
const circleMarkers: TestCircleMarker[] = [];

interface TestCircleMarker {
  latlng: { lat: number; lng: number };
  tooltip?: string;
  map?: TestMap;
  broughtToFront: number;
  bindTooltip(text: string): TestCircleMarker;
  addTo(map: TestMap): TestCircleMarker;
  setLatLng(latlng: { lat: number; lng: number }): TestCircleMarker;
  bringToFront(): TestCircleMarker;
}

interface TestMap {
  options: { maxBounds?: { contains(latlng: { lat: number; lng: number }): boolean } };
  zoom: number;
  locate: ReturnType<typeof vi.fn>;
  setView: ReturnType<typeof vi.fn>;
  getZoom(): number;
}

const leaflet = {
  latLng(lat: number, lng: number) {
    return { lat, lng };
  },
  circleMarker(latlng: { lat: number; lng: number }) {
    const marker: TestCircleMarker = {
      latlng,
      broughtToFront: 0,
      bindTooltip(text) {
        this.tooltip = text;
        return this;
      },
      addTo(map) {
        this.map = map;
        return this;
      },
      setLatLng(next) {
        this.latlng = next;
        return this;
      },
      bringToFront() {
        this.broughtToFront += 1;
        return this;
      },
    };
    circleMarkers.push(marker);
    return marker;
  },
};

vi.doMock('leaflet', () => ({ default: leaflet }));
vi.doMock('@capacitor/core', () => ({
  Capacitor: { isNativePlatform: () => nativePlatform },
}));
vi.doMock('@capacitor/geolocation', () => ({
  Geolocation: { requestPermissions, getCurrentPosition },
}));

const { createGeolocation } = await import('../src/lib/map/geolocation');

function createMap(contains = true): TestMap {
  return {
    options: { maxBounds: { contains: () => contains } },
    zoom: 12,
    locate: vi.fn(),
    setView: vi.fn(),
    getZoom() {
      return this.zoom;
    },
  };
}

beforeEach(() => {
  nativePlatform = false;
  requestPermissions.mockReset();
  getCurrentPosition.mockReset();
  circleMarkers.length = 0;
});

describe('createGeolocation', () => {
  it('delivers an inside-city web location and preserves marker behavior', () => {
    const map = createMap();
    const flash = vi.fn();
    const clear = vi.fn();
    const onLocation = vi.fn();
    const geo = createGeolocation(map as never, { flash, clear }, onLocation);

    geo.applyUserLocation(43.01, -83.61);

    expect(clear).toHaveBeenCalledOnce();
    expect(onLocation).toHaveBeenCalledWith({ lat: 43.01, lng: -83.61 });
    expect(map.setView).toHaveBeenCalledWith({ lat: 43.01, lng: -83.61 }, 15);
    expect(circleMarkers).toHaveLength(1);
    expect(circleMarkers[0]).toMatchObject({
      latlng: { lat: 43.01, lng: -83.61 },
      tooltip: 'You are here',
      map,
      broughtToFront: 1,
    });
    expect(flash).not.toHaveBeenCalled();
  });

  it('delivers an outside-city location without moving or marking the map', () => {
    const map = createMap(false);
    const flash = vi.fn();
    const onLocation = vi.fn();
    const geo = createGeolocation(map as never, { flash, clear: vi.fn() }, onLocation);

    geo.applyUserLocation(42.5, -84);

    expect(onLocation).toHaveBeenCalledWith({ lat: 42.5, lng: -84 });
    expect(flash).toHaveBeenCalledWith(
      'You appear to be outside Burton — showing the closest places on the city map.',
    );
    expect(map.setView).not.toHaveBeenCalled();
    expect(circleMarkers).toHaveLength(0);
  });

  it('uses Leaflet locate on web with the current locating message', () => {
    const map = createMap();
    const flash = vi.fn();
    const geo = createGeolocation(map as never, { flash, clear: vi.fn() }, vi.fn());

    geo.locateMe();

    expect(flash).toHaveBeenCalledWith('Locating…');
    expect(map.locate).toHaveBeenCalledWith({ enableHighAccuracy: true });
  });

  it('delivers native coordinates through the same callback', async () => {
    nativePlatform = true;
    requestPermissions.mockResolvedValue({ location: 'granted', coarseLocation: 'granted' });
    getCurrentPosition.mockResolvedValue({ coords: { latitude: 43.02, longitude: -83.62 } });
    const onLocation = vi.fn();
    const geo = createGeolocation(
      createMap() as never,
      { flash: vi.fn(), clear: vi.fn() },
      onLocation,
    );

    geo.locateMe();

    await vi.waitFor(() => expect(onLocation).toHaveBeenCalledWith({ lat: 43.02, lng: -83.62 }));
    expect(getCurrentPosition).toHaveBeenCalledWith({ enableHighAccuracy: true });
  });

  it('preserves native denial and failure messages', async () => {
    nativePlatform = true;
    const flash = vi.fn();
    requestPermissions.mockResolvedValueOnce({ location: 'denied', coarseLocation: 'denied' });
    const denied = createGeolocation(createMap() as never, { flash, clear: vi.fn() }, vi.fn());

    denied.locateMe();
    await vi.waitFor(() =>
      expect(flash).toHaveBeenCalledWith(
        'Couldn’t get your location — location access is turned off for this app.',
      ),
    );

    requestPermissions.mockRejectedValueOnce(new Error('permission failure'));
    const failed = createGeolocation(createMap() as never, { flash, clear: vi.fn() }, vi.fn());
    failed.locateMe();
    await vi.waitFor(() =>
      expect(flash).toHaveBeenCalledWith(
        'Couldn’t get your location — check that location access is allowed for this app.',
      ),
    );
  });
});

