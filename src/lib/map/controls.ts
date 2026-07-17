import L from 'leaflet';
import { Capacitor } from '@capacitor/core';

export interface MapControlCallbacks {
  onLocate: () => void;
  onReport: () => void;
}

export interface MapControlsHandle {
  destroy(): void;
}

interface ActionControlOptions {
  label: string;
  icon: string;
  title: string;
  ariaLabel: string;
  onActivate: () => void;
}

function installActionControl(map: L.Map, options: ActionControlOptions): L.Control {
  let button: HTMLButtonElement | undefined;
  const activate = () => options.onActivate();
  const ActionControl = L.Control.extend({
    options: { position: 'topleft' as L.ControlPosition },
    onAdd() {
      button = L.DomUtil.create('button', 'near-me-btn') as HTMLButtonElement;
      button.type = 'button';
      button.title = options.title;
      button.setAttribute('aria-label', options.ariaLabel);
      const icon = L.DomUtil.create('span');
      icon.setAttribute('aria-hidden', 'true');
      icon.textContent = options.icon;
      button.append(icon, ` ${options.label}`);
      L.DomEvent.disableClickPropagation(button);
      L.DomEvent.on(button, 'click', activate);
      return button;
    },
    onRemove() {
      if (!button) return;
      L.DomEvent.off(button);
      button = undefined;
    },
  });
  const control = new ActionControl();
  map.addControl(control);
  return control;
}

export function createMapControls(
  map: L.Map,
  callbacks: MapControlCallbacks,
): MapControlsHandle {
  const controls: L.Control[] = [];
  let destroyed = false;

  if (!Capacitor.isNativePlatform()) {
    controls.push(
      installActionControl(map, {
        label: 'Near me',
        icon: '◎',
        title: 'Center the map on my location',
        ariaLabel: 'Center the map on my location',
        onActivate: callbacks.onLocate,
      }),
      installActionControl(map, {
        label: 'Report an issue',
        icon: '⚠',
        title: 'Report an issue (pothole, sign, drainage, streetlight)',
        ariaLabel: 'Report an issue',
        onActivate: callbacks.onReport,
      }),
    );
  }

  return {
    destroy() {
      if (destroyed) return;
      destroyed = true;
      for (const control of controls) control.remove();
      controls.length = 0;
    },
  };
}

