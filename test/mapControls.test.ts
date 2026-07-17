import { beforeEach, describe, expect, it, vi } from 'vitest';

type Handler = () => void;

interface TestElement {
  tagName: string;
  className: string;
  type: string;
  title: string;
  textContent: string;
  children: TestElement[];
  attributes: Map<string, string>;
  listeners: Map<string, Set<Handler>>;
  append(...nodes: (TestElement | string)[]): void;
  setAttribute(name: string, value: string): void;
}

interface TestControl {
  options: { position: string };
  _map?: TestMap;
  _container?: TestElement;
  onAdd(map: TestMap): TestElement;
  onRemove?(map: TestMap): void;
  addTo(map: TestMap): TestControl;
  remove(): TestControl;
}

interface TestMap {
  controls: TestControl[];
  removedControls: TestControl[];
  addControl(control: TestControl): TestMap;
  removeControl(control: TestControl): TestMap;
}

function createElement(tagName: string, className = ''): TestElement {
  return {
    tagName,
    className,
    type: '',
    title: '',
    textContent: '',
    children: [],
    attributes: new Map(),
    listeners: new Map(),
    append(...nodes) {
      for (const node of nodes) {
        if (typeof node === 'string') this.textContent += node;
        else this.children.push(node);
      }
    },
    setAttribute(name, value) {
      this.attributes.set(name, value);
    },
  };
}

function createMap(): TestMap {
  return {
    controls: [],
    removedControls: [],
    addControl(control) {
      control._map = this;
      control._container = control.onAdd(this);
      this.controls.push(control);
      return this;
    },
    removeControl(control) {
      if (!this.controls.includes(control)) return this;
      control.onRemove?.(this);
      this.controls = this.controls.filter((candidate) => candidate !== control);
      this.removedControls.push(control);
      control._map = undefined;
      return this;
    },
  };
}

let nativePlatform = false;
const propagationDisabled = new Set<TestElement>();

const leaflet = {
  Control: {
    extend(definition: {
      options: { position: string };
      onAdd(this: TestControl, map: TestMap): TestElement;
      onRemove?(this: TestControl, map: TestMap): void;
    }) {
      return class implements TestControl {
        options = definition.options;
        _map?: TestMap;
        _container?: TestElement;

        onAdd(map: TestMap): TestElement {
          return definition.onAdd.call(this, map);
        }

        onRemove(map: TestMap): void {
          definition.onRemove?.call(this, map);
        }

        addTo(map: TestMap): TestControl {
          map.addControl(this);
          return this;
        }

        remove(): TestControl {
          this._map?.removeControl(this);
          return this;
        }
      };
    },
  },
  DomUtil: {
    create(tagName: string, className = '') {
      return createElement(tagName, className);
    },
  },
  DomEvent: {
    disableClickPropagation(element: TestElement) {
      propagationDisabled.add(element);
      for (const event of ['mousedown', 'touchstart', 'dblclick', 'contextmenu']) {
        element.listeners.set(event, new Set([() => {}]));
      }
    },
    on(element: TestElement, event: string, handler: Handler) {
      const handlers = element.listeners.get(event) ?? new Set<Handler>();
      handlers.add(handler);
      element.listeners.set(event, handlers);
    },
    off(element: TestElement, event?: string, handler?: Handler) {
      if (!event) {
        element.listeners.clear();
        return;
      }
      const handlers = element.listeners.get(event);
      if (handler) handlers?.delete(handler);
      else handlers?.clear();
      if (handlers?.size === 0) element.listeners.delete(event);
    },
  },
};

vi.doMock('leaflet', () => ({ default: leaflet }));
vi.doMock('@capacitor/core', () => ({
  Capacitor: { isNativePlatform: () => nativePlatform },
}));

const { createMapControls } = await import('../src/lib/map/controls');

function click(element: TestElement): void {
  for (const handler of element.listeners.get('click') ?? []) handler();
}

function visibleText(element: TestElement): string {
  return `${element.children.map((child) => child.textContent).join('')}${element.textContent}`;
}

beforeEach(() => {
  nativePlatform = false;
  propagationDisabled.clear();
});

describe('createMapControls', () => {
  it('installs the exact web locate and report controls and invokes typed callbacks', () => {
    const map = createMap();
    const onLocate = vi.fn();
    const onReport = vi.fn();

    const handle = createMapControls(map as never, { onLocate, onReport });

    expect(map.controls).toHaveLength(2);
    const [locate, report] = map.controls.map((control) => control._container!);
    expect(map.controls.map((control) => control.options.position)).toEqual(['topleft', 'topleft']);
    expect([locate.className, report.className]).toEqual(['near-me-btn', 'near-me-btn']);
    expect([locate.type, report.type]).toEqual(['button', 'button']);
    expect(locate.title).toBe('Center the map on my location');
    expect(locate.attributes.get('aria-label')).toBe('Center the map on my location');
    expect(visibleText(locate)).toBe('◎ Near me');
    expect(locate.children[0].attributes.get('aria-hidden')).toBe('true');
    expect(report.title).toBe('Report an issue (pothole, sign, drainage, streetlight)');
    expect(report.attributes.get('aria-label')).toBe('Report an issue');
    expect(visibleText(report)).toBe('⚠ Report an issue');
    expect(report.children[0].attributes.get('aria-hidden')).toBe('true');
    expect(propagationDisabled).toEqual(new Set([locate, report]));

    click(locate);
    click(report);

    expect(onLocate).toHaveBeenCalledOnce();
    expect(onReport).toHaveBeenCalledOnce();
    handle.destroy();
  });

  it('does not install desktop controls on a native platform', () => {
    nativePlatform = true;
    const map = createMap();

    const handle = createMapControls(map as never, { onLocate: vi.fn(), onReport: vi.fn() });

    expect(map.controls).toHaveLength(0);
    handle.destroy();
    expect(map.removedControls).toHaveLength(0);
  });

  it('removes DOM listeners and Leaflet controls exactly once', () => {
    const map = createMap();
    const onLocate = vi.fn();
    const onReport = vi.fn();
    const handle = createMapControls(map as never, { onLocate, onReport });
    const buttons = map.controls.map((control) => control._container!);

    handle.destroy();
    handle.destroy();

    expect(map.controls).toHaveLength(0);
    expect(map.removedControls).toHaveLength(2);
    expect(buttons.map((button) => button.listeners.size)).toEqual([0, 0]);
    buttons.forEach(click);
    expect(onLocate).not.toHaveBeenCalled();
    expect(onReport).not.toHaveBeenCalled();
  });
});

