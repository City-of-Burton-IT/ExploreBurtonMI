type TestHandler = (...args: unknown[]) => void;

export interface TestElement {
  tagName: string;
  className: string;
  style: Record<string, string>;
  children: TestElement[];
  parentElement?: TestElement;
  attributes: Map<string, string>;
  listeners: Map<string, Set<TestHandler>>;
  textContent: string;
  title: string;
  type: string;
  src: string;
  alt: string;
  classList: {
    contains(name: string): boolean;
    toggle(name: string, force?: boolean): boolean;
  };
  appendChild(child: TestElement): TestElement;
  remove(): void;
  setAttribute(name: string, value: string): void;
  addEventListener(event: string, handler: TestHandler): void;
  removeEventListener(event: string, handler: TestHandler): void;
}

export function createTestElement(tagName = 'div', className = ''): TestElement {
  const classes = new Set(className.split(/\s+/).filter(Boolean));
  const element: TestElement = {
    tagName,
    className,
    style: {},
    children: [],
    attributes: new Map(),
    listeners: new Map(),
    textContent: '',
    title: '',
    type: '',
    src: '',
    alt: '',
    classList: {
      contains(name) {
        return classes.has(name);
      },
      toggle(name, force) {
        const add = force ?? !classes.has(name);
        if (add) classes.add(name);
        else classes.delete(name);
        element.className = [...classes].join(' ');
        return add;
      },
    },
    appendChild(child) {
      child.parentElement = this;
      this.children.push(child);
      return child;
    },
    remove() {
      if (!this.parentElement) return;
      this.parentElement.children = this.parentElement.children.filter((child) => child !== this);
      this.parentElement = undefined;
    },
    setAttribute(name, value) {
      this.attributes.set(name, value);
    },
    addEventListener(event, handler) {
      const handlers = this.listeners.get(event) ?? new Set<TestHandler>();
      handlers.add(handler);
      this.listeners.set(event, handlers);
    },
    removeEventListener(event, handler) {
      const handlers = this.listeners.get(event);
      handlers?.delete(handler);
      if (handlers?.size === 0) this.listeners.delete(event);
    },
  };
  return element;
}

export interface TestCircleMarker {
  latLng: [number, number];
  options: Record<string, unknown>;
  tooltip?: string;
  tooltipBound: boolean;
  closeTooltipCalls: number;
  unbindTooltipCalls: number;
  feature?: unknown;
  handlers: Map<string, Set<TestHandler>>;
  broughtToFront: boolean;
  bindTooltip(content: string): TestCircleMarker;
  closeTooltip(): TestCircleMarker;
  unbindTooltip(): TestCircleMarker;
  on(event: string, handler: TestHandler): TestCircleMarker;
  off(event?: string, handler?: TestHandler): TestCircleMarker;
  fire(event: string): void;
  setStyle(style: Record<string, unknown>): TestCircleMarker;
  bringToFront(): TestCircleMarker;
}

export interface TestMarkerClusterGroup {
  kind: 'markerClusterGroup';
  options: Record<string, unknown>;
  layers: TestCircleMarker[];
  handlers: Map<string, Set<TestHandler>>;
  map?: TestMap;
  clearLayersCalls: number;
  zoomToShowLayerCalls: TestCircleMarker[];
  deferZoomToShowLayerCallbacks: boolean;
  pendingZoomToShowLayerCallbacks: (() => void)[];
  clearLayers(): void;
  addLayers(layers: TestCircleMarker[]): void;
  hasLayer(layer: TestCircleMarker): boolean;
  on(event: string, handler: TestHandler): TestMarkerClusterGroup;
  off(event?: string, handler?: TestHandler): TestMarkerClusterGroup;
  fire(event: string, payload?: unknown): void;
  zoomToShowLayer(layer: TestCircleMarker, callback: () => void): void;
  flushZoomToShowLayerCallbacks(): void;
}

export type TestMapLayer = TestLayer | TestMarkerClusterGroup;

export interface TestBounds {
  points?: unknown[];
  padFactor?: number;
  pad(factor: number): TestBounds;
}

export interface TestLayer {
  kind: string;
  source?: unknown;
  options: Record<string, unknown>;
  handlers: Map<string, Set<TestHandler>>;
  map?: TestMap;
  element?: TestElement;
  addTo(map: TestMap): TestLayer;
  on(event: string, handler: TestHandler): TestLayer;
  off(event?: string, handler?: TestHandler): TestLayer;
  fire(event: string): void;
  getElement(): TestElement | undefined;
}

export interface TestGeoJsonLayer extends TestLayer {
  bounds: TestBounds;
  getBounds(): TestBounds;
}

export interface TestLayerControl {
  container: TestElement;
  overlays: { layer: TestLayer; label: string }[];
  removed: boolean;
  addTo(map: TestMap): TestLayerControl;
  addOverlay(layer: TestLayer, label: string): TestLayerControl;
  getContainer(): TestElement;
  remove(): TestLayerControl;
}

export interface TestMap {
  host: TestElement;
  options: Record<string, unknown>;
  layers: TestMapLayer[];
  controls: unknown[];
  panes: Map<string, TestElement>;
  center: { lat: number; lng: number };
  zoom: number;
  setMaxBoundsCalls: TestBounds[];
  fitBoundsCalls: TestBounds[];
  setViewCalls: { center: { lat: number; lng: number }; zoom: number; options?: unknown }[];
  invalidateSizeCalls: number;
  closePopupCalls: number;
  removeCalls: number;
  addLayer(layer: TestMapLayer): TestMap;
  removeLayer(layer: TestMapLayer): TestMap;
  hasLayer(layer: TestMapLayer): boolean;
  createPane(name: string): TestElement;
  getPane(name: string): TestElement | undefined;
  getCenter(): { lat: number; lng: number };
  getZoom(): number;
  setView(center: { lat: number; lng: number }, zoom: number, options?: unknown): TestMap;
  invalidateSize(): TestMap;
  setMaxBounds(bounds: TestBounds): TestMap;
  fitBounds(bounds: TestBounds): TestMap;
  closePopup(): TestMap;
  remove(): TestMap;
}

function createEventedLayer(
  kind: string,
  source?: unknown,
  options: Record<string, unknown> = {},
): TestLayer {
  return {
    kind,
    source,
    options,
    handlers: new Map(),
    addTo(map) {
      map.addLayer(this);
      return this;
    },
    on(event, handler) {
      const handlers = this.handlers.get(event) ?? new Set<TestHandler>();
      handlers.add(handler);
      this.handlers.set(event, handlers);
      return this;
    },
    off(event, handler) {
      if (!event) this.handlers.clear();
      else if (!handler) this.handlers.delete(event);
      else {
        const handlers = this.handlers.get(event);
        handlers?.delete(handler);
        if (handlers?.size === 0) this.handlers.delete(event);
      }
      return this;
    },
    fire(event) {
      for (const handler of this.handlers.get(event) ?? []) handler();
    },
    getElement() {
      return this.element;
    },
  };
}

export interface LeafletTestDouble {
  maps: TestMap[];
  circleMarkers: TestCircleMarker[];
  markerClusterGroups: TestMarkerClusterGroup[];
  tileLayers: TestLayer[];
  geoJsonLayers: TestGeoJsonLayer[];
  imageOverlays: TestLayer[];
  layerControls: TestLayerControl[];
  scaleControls: { options: Record<string, unknown>; map?: TestMap }[];
  map(host: TestElement, options: Record<string, unknown>): TestMap;
  latLngBounds(first: unknown, second: unknown): TestBounds;
  tileLayer(source: string, options: Record<string, unknown>): TestLayer;
  geoJSON(source: unknown, options: Record<string, unknown>): TestGeoJsonLayer;
  imageOverlay(source: string, bounds: unknown, options: Record<string, unknown>): TestLayer;
  layerGroup(): TestLayer;
  circleMarker(latLng: [number, number], options: Record<string, unknown>): TestCircleMarker;
  markerClusterGroup(options?: Record<string, unknown>): TestMarkerClusterGroup;
  control: {
    scale(options: Record<string, unknown>): { addTo(map: TestMap): unknown };
    layers(): TestLayerControl;
  };
  DomUtil: {
    create(tagName: string, className?: string, parent?: TestElement): TestElement;
  };
  DomEvent: {
    on(element: TestElement, event: string, handler: TestHandler): void;
    off(element: TestElement, event?: string, handler?: TestHandler): void;
    stop(event: unknown): void;
    disableClickPropagation(element: TestElement): void;
    disableScrollPropagation(element: TestElement): void;
  };
}

export function createLeafletTestDouble(): LeafletTestDouble {
  const testDouble: LeafletTestDouble = {
    maps: [],
    circleMarkers: [],
    markerClusterGroups: [],
    tileLayers: [],
    geoJsonLayers: [],
    imageOverlays: [],
    layerControls: [],
    scaleControls: [],
    map(host, options) {
      const map: TestMap = {
        host,
        options,
        layers: [],
        controls: [],
        panes: new Map([['tooltipPane', createTestElement('div', 'tooltipPane')]]),
        center: { lat: 0, lng: 0 },
        zoom: Number(options.zoom ?? 0),
        setMaxBoundsCalls: [],
        fitBoundsCalls: [],
        setViewCalls: [],
        invalidateSizeCalls: 0,
        closePopupCalls: 0,
        removeCalls: 0,
        addLayer(layer) {
          if (!this.layers.includes(layer)) this.layers.push(layer);
          layer.map = this;
          layer.fire('add');
          return this;
        },
        removeLayer(layer) {
          this.layers = this.layers.filter((candidate) => candidate !== layer);
          layer.fire('remove');
          layer.map = undefined;
          return this;
        },
        hasLayer(layer) {
          return this.layers.includes(layer);
        },
        createPane(name) {
          const pane = createTestElement('div', name);
          this.panes.set(name, pane);
          return pane;
        },
        getPane(name) {
          return this.panes.get(name);
        },
        getCenter() {
          return { ...this.center };
        },
        getZoom() {
          return this.zoom;
        },
        setView(center, zoom, viewOptions) {
          this.center = { ...center };
          this.zoom = zoom;
          this.setViewCalls.push({ center: { ...center }, zoom, options: viewOptions });
          return this;
        },
        invalidateSize() {
          this.invalidateSizeCalls += 1;
          return this;
        },
        setMaxBounds(bounds) {
          this.setMaxBoundsCalls.push(bounds);
          return this;
        },
        fitBounds(bounds) {
          this.fitBoundsCalls.push(bounds);
          return this;
        },
        closePopup() {
          this.closePopupCalls += 1;
          return this;
        },
        remove() {
          this.removeCalls += 1;
          return this;
        },
      };
      const center = options.center as [number, number] | undefined;
      if (center) map.center = { lat: center[0], lng: center[1] };
      testDouble.maps.push(map);
      return map;
    },
    latLngBounds(first, second) {
      return {
        points: [first, second],
        pad(factor) {
          return { ...this, padFactor: factor };
        },
      };
    },
    tileLayer(source, options) {
      const layer = createEventedLayer('tile', source, options);
      testDouble.tileLayers.push(layer);
      return layer;
    },
    geoJSON(source, options) {
      const bounds: TestBounds = {
        pad(factor) {
          return { ...this, padFactor: factor };
        },
      };
      const layer = createEventedLayer('geoJSON', source, options) as TestGeoJsonLayer;
      layer.bounds = bounds;
      layer.getBounds = () => bounds;
      testDouble.geoJsonLayers.push(layer);
      return layer;
    },
    imageOverlay(source, bounds, options) {
      const layer = createEventedLayer('imageOverlay', { source, bounds }, options);
      layer.element = createTestElement('img');
      testDouble.imageOverlays.push(layer);
      return layer;
    },
    layerGroup() {
      const layer = createEventedLayer('layerGroup');
      const children: TestLayer[] = [];
      const group = layer as TestLayer & {
        addLayer(child: TestLayer): void;
        clearLayers(): void;
      };
      group.addLayer = (child) => {
        children.push(child);
      };
      group.clearLayers = () => {
        children.length = 0;
      };
      return layer;
    },
    circleMarker(latLng, options) {
      const marker: TestCircleMarker = {
        latLng,
        options: { ...options },
        tooltipBound: false,
        closeTooltipCalls: 0,
        unbindTooltipCalls: 0,
        handlers: new Map(),
        broughtToFront: false,
        bindTooltip(content) {
          this.tooltip = content;
          this.tooltipBound = true;
          return this;
        },
        closeTooltip() {
          this.closeTooltipCalls += 1;
          return this;
        },
        unbindTooltip() {
          this.unbindTooltipCalls += 1;
          this.tooltipBound = false;
          return this;
        },
        on(event, handler) {
          const handlers = this.handlers.get(event) ?? new Set<TestHandler>();
          handlers.add(handler);
          this.handlers.set(event, handlers);
          return this;
        },
        off(event, handler) {
          if (!event) this.handlers.clear();
          else if (!handler) this.handlers.delete(event);
          else {
            const handlers = this.handlers.get(event);
            handlers?.delete(handler);
            if (handlers?.size === 0) this.handlers.delete(event);
          }
          return this;
        },
        fire(event) {
          for (const handler of this.handlers.get(event) ?? []) handler();
        },
        setStyle(style) {
          Object.assign(this.options, style);
          return this;
        },
        bringToFront() {
          this.broughtToFront = true;
          return this;
        },
      };
      testDouble.circleMarkers.push(marker);
      return marker;
    },
    markerClusterGroup(options = {}) {
      const group: TestMarkerClusterGroup = {
        kind: 'markerClusterGroup',
        options,
        layers: [],
        handlers: new Map(),
        clearLayersCalls: 0,
        zoomToShowLayerCalls: [],
        deferZoomToShowLayerCallbacks: false,
        pendingZoomToShowLayerCallbacks: [],
        clearLayers() {
          this.clearLayersCalls += 1;
          this.layers = [];
        },
        addLayers(layers) {
          this.layers.push(...layers);
        },
        hasLayer(layer) {
          return this.layers.includes(layer);
        },
        on(event, handler) {
          const handlers = this.handlers.get(event) ?? new Set<TestHandler>();
          handlers.add(handler);
          this.handlers.set(event, handlers);
          return this;
        },
        off(event, handler) {
          if (!event) this.handlers.clear();
          else if (!handler) this.handlers.delete(event);
          else {
            const handlers = this.handlers.get(event);
            handlers?.delete(handler);
            if (handlers?.size === 0) this.handlers.delete(event);
          }
          return this;
        },
        fire(event, payload) {
          for (const handler of this.handlers.get(event) ?? []) handler(payload);
        },
        zoomToShowLayer(layer, callback) {
          if (!this.hasLayer(layer)) {
            throw new Error('zoomToShowLayer requires a current cluster member');
          }
          this.zoomToShowLayerCalls.push(layer);
          if (this.deferZoomToShowLayerCallbacks) {
            this.pendingZoomToShowLayerCallbacks.push(callback);
          } else {
            callback();
          }
        },
        flushZoomToShowLayerCallbacks() {
          const callbacks = this.pendingZoomToShowLayerCallbacks.splice(0);
          for (const callback of callbacks) callback();
        },
      };
      testDouble.markerClusterGroups.push(group);
      return group;
    },
    control: {
      scale(options) {
        const control = {
          options,
          map: undefined as TestMap | undefined,
          addTo(map: TestMap) {
            this.map = map;
            map.controls.push(this);
            return this;
          },
        };
        testDouble.scaleControls.push(control);
        return control;
      },
      layers() {
        const container = createTestElement('div', 'leaflet-control-layers');
        const control: TestLayerControl = {
          container,
          overlays: [],
          removed: false,
          addTo(map) {
            map.controls.push(this);
            return this;
          },
          addOverlay(layer, label) {
            this.overlays.push({ layer, label });
            return this;
          },
          getContainer() {
            return this.container;
          },
          remove() {
            this.removed = true;
            return this;
          },
        };
        testDouble.layerControls.push(control);
        return control;
      },
    },
    DomUtil: {
      create(tagName, className = '', parent) {
        const element = createTestElement(tagName, className);
        parent?.appendChild(element);
        return element;
      },
    },
    DomEvent: {
      on(element, event, handler) {
        element.addEventListener(event, handler);
      },
      off(element, event, handler) {
        if (!event) element.listeners.clear();
        else if (!handler) element.listeners.delete(event);
        else element.removeEventListener(event, handler);
      },
      stop() {},
      disableClickPropagation() {},
      disableScrollPropagation() {},
    },
  };
  return testDouble;
}

