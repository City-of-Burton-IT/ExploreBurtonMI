<script lang="ts">
  import { trendLayout, multiTrendLayout, formatValue, CIVIC_BLUE } from './scale';
  import ChartTip from './ChartTip.svelte';

  let {
    points = [],
    unit = '',
    markers = [],
    lines,
  }: {
    points?: { x: string; y: number }[];
    unit?: string;
    markers?: { x: string; label: string }[];
    lines?: { label: string; points: { x: string; y: number }[]; color?: string }[];
  } = $props();

  const W = 320;
  const H = 150;
  const PAD = 28;

  const isMulti = $derived(!!(lines && lines.length));
  const single = $derived(trendLayout(points, W, H, PAD));
  const multi = $derived(isMulti && lines ? multiTrendLayout(lines, W, H, PAD) : null);

  // One unified list of lines to draw; a single-line trend is wrapped as one.
  const drawLines = $derived(
    multi
      ? multi.lines
      : [{ label: '', color: CIVIC_BLUE, polyline: single.polyline, dots: single.dots }],
  );
  const xLabels = $derived(multi ? multi.xLabels : single.dots.map((d) => d.label));

  function xCoordOf(label: string): number {
    const n = xLabels.length;
    const step = n > 1 ? (W - 2 * PAD) / (n - 1) : 0;
    const i = xLabels.indexOf(label);
    return n > 1 ? PAD + i * step : PAD;
  }
  // Markers attach to real data points only -- ignore any x that isn't on the axis.
  const markerHits = $derived(markers.filter((m) => xLabels.includes(m.x)));

  // Dense axis: thin x labels to ~6 (same rule as before). Single-line keeps its
  // endpoint value labels; multi-line omits per-point value labels (too busy).
  const dense = $derived(xLabels.length > 8);
  const xLabelIdx = $derived.by(() => {
    const n = xLabels.length;
    if (!dense) return null;
    const count = Math.min(6, Math.floor((n - 1) / 2) + 1);
    const set = new Set<number>();
    for (let k = 0; k < count; k++) set.add(Math.round((k * (n - 1)) / (count - 1)));
    return set;
  });
  const showXLabel = (i: number) => !dense || (xLabelIdx?.has(i) ?? true);
  const lastIdx = $derived(single.dots.length - 1);
  const showVLabel = (i: number) => !dense || i === 0 || i === lastIdx;

  let host: HTMLDivElement | undefined = $state();
  let active = $state<[number, number] | null>(null); // [lineIndex, dotIndex]
  let tip = $state({ x: 0, y: 0 });

  function atPointer(e: PointerEvent, li: number, di: number) {
    if (!host) return;
    const r = host.getBoundingClientRect();
    tip = { x: e.clientX - r.left, y: e.clientY - r.top };
    active = [li, di];
  }
  function atFocus(e: FocusEvent, li: number, di: number) {
    if (!host) return;
    const r = (e.currentTarget as SVGCircleElement).getBoundingClientRect();
    const hr = host.getBoundingClientRect();
    tip = { x: r.left - hr.left + r.width / 2, y: r.top - hr.top + r.height / 2 };
    active = [li, di];
  }
  const activeDot = $derived(active ? (drawLines[active[0]]?.dots[active[1]] ?? null) : null);
  const activeLineLabel = $derived(active ? (drawLines[active[0]]?.label ?? '') : '');
  const tipLabel = $derived(
    activeDot ? (activeLineLabel ? `${activeLineLabel} · ${activeDot.label}` : activeDot.label) : '',
  );
  const isActive = (li: number, di: number) => !!active && active[0] === li && active[1] === di;
</script>

{#if drawLines.every((l) => l.dots.length === 0)}
  <p class="nodata">No data available.</p>
{:else}
  <div class="chart-host" bind:this={host}>
    <svg viewBox="0 0 {W} {H}" role="img" aria-label="Trend over time" class="trend">
      <!-- baseline -->
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} class="axis" />

      <!-- event markers (attach to real data points) -->
      {#each markerHits as m (m.x)}
        {@const mx = xCoordOf(m.x)}
        <line x1={mx} y1={PAD - 2} x2={mx} y2={H - PAD} class="marker-line" />
        <text x={mx} y={PAD - 6} class="marker-label">{m.label}</text>
      {/each}

      <!-- hover guide for the active point -->
      {#if activeDot}
        <line x1={activeDot.x} y1={PAD - 4} x2={activeDot.x} y2={H - PAD} class="guide" />
      {/if}

      <!-- one polyline + dots per line -->
      {#each drawLines as ln, li (li)}
        {#if ln.dots.length > 1}
          <polyline points={ln.polyline} fill="none" stroke={ln.color} stroke-width="2.5" />
        {/if}
        {#each ln.dots as d, di (d.label)}
          <circle cx={d.x} cy={d.y} r={isActive(li, di) ? 5.5 : 3.5} fill={ln.color} class="dot" />
          {#if !isMulti && showVLabel(di)}
            <text x={d.x} y={d.y - 8} class="vlabel" class:hide={isActive(li, di)}>{formatValue(d.value, unit)}</text>
          {/if}
          <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
          <circle
            cx={d.x}
            cy={d.y}
            r="13"
            fill="transparent"
            class="hit"
            role="img"
            tabindex="0"
            aria-label="{ln.label ? ln.label + ', ' : ''}{d.label}: {formatValue(d.value, unit)}"
            onpointerenter={(e) => atPointer(e, li, di)}
            onpointermove={(e) => atPointer(e, li, di)}
            onpointerleave={() => (active = null)}
            onpointerdown={(e) => atPointer(e, li, di)}
            onfocus={(e) => atFocus(e, li, di)}
            onblur={() => (active = null)}
          />
        {/each}
      {/each}

      <!-- shared x-axis labels -->
      {#each xLabels as lbl, i (lbl)}
        {#if showXLabel(i)}
          <text x={xCoordOf(lbl)} y={H - PAD + 16} class="xlabel">{lbl}</text>
        {/if}
      {/each}
    </svg>

    {#if isMulti}
      <ul class="legend">
        {#each drawLines as ln (ln.label)}
          <li><span class="swatch" style:background={ln.color}></span>{ln.label}</li>
        {/each}
      </ul>
    {/if}

    <ChartTip
      x={tip.x}
      y={tip.y}
      show={!!activeDot}
      label={tipLabel}
      value={activeDot ? formatValue(activeDot.value, unit) : ''}
    />
  </div>
{/if}

<style>
  .chart-host {
    position: relative;
  }
  .trend {
    width: 100%;
    max-width: 420px;
    height: auto;
  }
  .axis {
    stroke: #d8dde4;
    stroke-width: 1;
  }
  .guide {
    stroke: var(--civic-blue, #2c57a0);
    stroke-width: 1;
    stroke-dasharray: 3 3;
    opacity: 0.5;
  }
  .marker-line {
    stroke: var(--pub-muted, #5c5c5c);
    stroke-width: 1;
    stroke-dasharray: 2 2;
    opacity: 0.55;
  }
  .marker-label {
    font-size: 9px;
    fill: var(--pub-muted, #5c5c5c);
    text-anchor: middle;
    font-family: var(--font-body, sans-serif);
  }
  .dot {
    transition: r 0.12s;
  }
  .hit {
    cursor: pointer;
  }
  .hit:focus-visible {
    outline: none;
    stroke: var(--civic-blue, #2c57a0);
    stroke-width: 2;
  }
  .xlabel {
    font-size: 10px;
    fill: #666;
    text-anchor: middle;
    font-family: var(--font-body, sans-serif);
  }
  .vlabel {
    font-size: 10px;
    fill: #333;
    text-anchor: middle;
    font-weight: 600;
    font-family: var(--font-body, sans-serif);
  }
  .vlabel.hide {
    opacity: 0;
  }
  .legend {
    list-style: none;
    margin: 0.4rem 0 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem 0.9rem;
    font-size: 0.8rem;
    color: var(--pub-ink, #2c2c2c);
  }
  .legend li {
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }
  .swatch {
    width: 0.75rem;
    height: 0.2rem;
    border-radius: 2px;
    flex: 0 0 auto;
  }
  .nodata {
    color: var(--pub-muted, #5c5c5c);
    font-size: 0.9rem;
    font-style: italic;
  }
</style>
