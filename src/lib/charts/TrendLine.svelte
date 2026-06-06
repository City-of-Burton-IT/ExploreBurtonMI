<script lang="ts">
  import { trendLayout, formatValue } from './scale';
  import ChartTip from './ChartTip.svelte';

  let {
    points,
    unit = '',
  }: { points: { x: string; y: number }[]; unit?: string } = $props();

  const W = 320;
  const H = 150;
  const PAD = 28;

  const layout = $derived(trendLayout(points, W, H, PAD));
  const color = '#2c57a0'; // civic blue

  let host: HTMLDivElement | undefined = $state();
  let active = $state(-1);
  let tip = $state({ x: 0, y: 0 });

  function atPointer(e: PointerEvent, i: number) {
    if (!host) return;
    const r = host.getBoundingClientRect();
    tip = { x: e.clientX - r.left, y: e.clientY - r.top };
    active = i;
  }
  const dot = $derived(active >= 0 ? layout.dots[active] : null);
</script>

{#if layout.dots.length === 0}
  <p class="nodata">No data available.</p>
{:else}
  <div class="chart-host" bind:this={host}>
    <svg viewBox="0 0 {W} {H}" role="img" aria-label="Trend over time" class="trend">
      <!-- baseline -->
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} class="axis" />
      <!-- hover guide line for the active point -->
      {#if dot}
        <line x1={dot.x} y1={PAD - 4} x2={dot.x} y2={H - PAD} class="guide" />
      {/if}
      {#if layout.dots.length > 1}
        <polyline points={layout.polyline} fill="none" stroke={color} stroke-width="2.5" />
      {/if}
      {#each layout.dots as d, i (d.label)}
        <circle cx={d.x} cy={d.y} r={active === i ? 5.5 : 3.5} fill={color} class="dot" />
        <text x={d.x} y={H - PAD + 16} class="xlabel">{d.label}</text>
        <text x={d.x} y={d.y - 8} class="vlabel" class:hide={active === i}>{formatValue(d.value, unit)}</text>
        <!-- transparent wide hit target for easy hover/tap/focus -->
        <circle
          cx={d.x}
          cy={d.y}
          r="13"
          fill="transparent"
          class="hit"
          role="img"
          aria-label="{d.label}: {formatValue(d.value, unit)}"
          onpointerenter={(e) => atPointer(e, i)}
          onpointermove={(e) => atPointer(e, i)}
          onpointerleave={() => (active = -1)}
          onpointerdown={(e) => atPointer(e, i)}
        />
      {/each}
    </svg>
    <ChartTip
      x={tip.x}
      y={tip.y}
      show={active >= 0}
      label={dot?.label ?? ''}
      value={dot ? formatValue(dot.value, unit) : ''}
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
  /* Hide the static value label for the active point (the tooltip shows it). */
  .vlabel.hide {
    opacity: 0;
  }
  .nodata {
    color: #888;
    font-size: 0.9rem;
    font-style: italic;
  }
</style>
