// "Near me" geolocation: the web (Leaflet locate) and native (Capacitor
// Geolocation) paths, feeding one shared position handler.
import L from 'leaflet';
import { Capacitor } from '@capacitor/core';
import { Geolocation } from '@capacitor/geolocation';

export interface LocateMessenger {
  /** show a transient status/error toast (auto-clears) */
  flash: (msg: string) => void;
  /** clear any showing toast immediately */
  clear: () => void;
}

export interface MapGeolocation {
  /** handle a found position (shared by the web + native paths) */
  applyUserLocation: (lat: number, lng: number) => void;
  /** locate the user via the right path for the platform */
  locateMe: () => void;
}

export type LocationCallback = (location: { lat: number; lng: number }) => void;

export function createGeolocation(
  map: L.Map,
  msg: LocateMessenger,
  onLocation: LocationCallback,
): MapGeolocation {
  let userMarker: L.CircleMarker | undefined;

  // Shared "we have the user's position" handler for both the web (Leaflet locate)
  // and native (Capacitor Geolocation) paths: sort the list nearest-first, and only
  // recenter + drop the "you are here" marker when the user is inside the city bounds.
  function applyUserLocation(lat: number, lng: number): void {
    msg.clear();
    const latlng = L.latLng(lat, lng);
    onLocation({ lat, lng });
    // maxBounds is a LatLngBounds at construction (tightened to the city outline on
    // load), so it's a bounds instance at runtime.
    const bounds = map.options.maxBounds as L.LatLngBounds | undefined;
    if (bounds && !bounds.contains(latlng)) {
      msg.flash('You appear to be outside Burton — showing the closest places on the city map.');
      return;
    }
    map.setView(latlng, Math.max(map.getZoom(), 15));
    if (!userMarker) {
      userMarker = L.circleMarker(latlng, {
        radius: 8,
        color: '#ffffff',
        weight: 3,
        fillColor: '#1976d2',
        fillOpacity: 1,
      });
      userMarker.bindTooltip('You are here');
      userMarker.addTo(map);
    } else {
      userMarker.setLatLng(latlng);
    }
    userMarker.bringToFront();
  }

  // Native (Capacitor) geolocation: request the runtime permission, then read one
  // position. Mirrors Leaflet's locationerror messaging on denial/failure.
  async function locateNative(): Promise<void> {
    try {
      const perm = await Geolocation.requestPermissions();
      if (perm.location === 'denied' && perm.coarseLocation === 'denied') {
        msg.flash('Couldn’t get your location — location access is turned off for this app.');
        return;
      }
      const pos = await Geolocation.getCurrentPosition({ enableHighAccuracy: true });
      applyUserLocation(pos.coords.latitude, pos.coords.longitude);
    } catch {
      msg.flash('Couldn’t get your location — check that location access is allowed for this app.');
    }
  }

  // "Near me": locate the user via the right path for the platform. Shared by the
  // map's own control button and the native quick-actions row (via ui.nearMeNonce).
  function locateMe(): void {
    msg.flash('Locating…');
    // No setView: we recenter ourselves only when the user is inside the city
    // bounds (the map is locked to Burton, so centering on a far-away user would
    // just clamp to the edge and leave their marker unreachable off-map).
    if (Capacitor.isNativePlatform()) {
      // In the native app the WebView's navigator.geolocation needs the Android
      // runtime permission, which Leaflet's map.locate() can't request. Use the
      // Capacitor Geolocation plugin to prompt + read the position, then feed it
      // through the same handler the web path uses.
      locateNative();
    } else {
      map.locate({ enableHighAccuracy: true });
    }
  }

  return { applyUserLocation, locateMe };
}

