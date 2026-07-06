// Shared hover/tooltip state for the chart components: which datum is active
// and where the ChartTip sits, positioned relative to the bound chart host.
// Generic over the active key so bars/donut (an index) and trend (a
// [line, dot] tuple) share one implementation.
export function createChartHover<K>(inactive: K) {
  let host: HTMLElement | undefined = $state();
  let active = $state(inactive) as K;
  let tip = $state({ x: 0, y: 0 });

  /** Place the tip at the pointer (host-relative) and mark `key` active. */
  function atPointer(e: PointerEvent, key: K): void {
    if (!host) return;
    const r = host.getBoundingClientRect();
    tip = { x: e.clientX - r.left, y: e.clientY - r.top };
    active = key;
  }

  /** Keyboard path: place the tip over the focused element's center. */
  function atFocus(e: FocusEvent, key: K): void {
    if (!host) return;
    const r = (e.currentTarget as Element).getBoundingClientRect();
    const hr = host.getBoundingClientRect();
    tip = { x: r.left - hr.left + r.width / 2, y: r.top - hr.top + r.height / 2 };
    active = key;
  }

  function clear(): void {
    active = inactive;
  }

  return {
    /** the chart's positioning container — wire with bind:this={hover.host} */
    get host() {
      return host;
    },
    set host(v: HTMLElement | undefined) {
      host = v;
    },
    get active() {
      return active;
    },
    get tip() {
      return tip;
    },
    atPointer,
    atFocus,
    clear,
  };
}
