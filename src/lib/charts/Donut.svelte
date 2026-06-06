<script lang="ts">
  import type { InfoSeriesItem } from '../types';
  import { donutSegments, formatValue } from './scale';
  import ChartTip from './ChartTip.svelte';

  let { series, unit = '' }: { series: InfoSeriesItem[]; unit?: string } = $props();

  const SIZE = 168;
  const R = 60;
  const STROKE = 26;
  const center = SIZE / 2;

  const layout = $derived(donutSegments(series, R));

  let host: HTMLDivElement | undefined = $state();
  let active = $state(-1);
  let tip = $state({ x: 0, y: 0 });

  function atPointer(e: PointerEvent, i: number) {
    if (!host) return;
    const r = host.getBoundingClientRect();
    tip = { x: e.clientX - r.left, y: e.clientY - r.top };
    active = i;
  }

  const seg = $derived(active >= 0 ? layout.segments[active] : null);
</script>

{#if layout.segments.length === 0}
  <p class="nodata">No data available.</p>
{:else}
  <div class="donut chart-host" bind:this={host}>
    <svg viewBox="0 0 {SIZE} {SIZE}" role="img" aria-label="Proportional breakdown">
      <g transform="rotate(-90 {center} {center})">
        {#each layout.segments as s, i (s.label)}
          <circle
            cx={center}
            cy={center}
            r={R}
            fill="none"
            stroke={s.color}
            stroke-width={active === i ? STROKE + 5 : STROKE}
            stroke-dasharray="{s.dash} {s.gap}"
            stroke-dashoffset={-s.offset}
            class="seg"
            class:dim={active >= 0 && active !== i}
            role="img"
            aria-label="{s.label}: {formatValue(s.value, unit)} ({Math.round(s.pct)}%)"
            onpointerenter={(e) => atPointer(e, i)}
            onpointermove={(e) => atPointer(e, i)}
            onpointerleave={() => (active = -1)}
            onpointerdown={(e) => atPointer(e, i)}
          />
        {/each}
      </g>
      <!-- Center label: the hovered slice, or the total at rest. -->
      <text x={center} y={center - 2} class="c-val">
        {seg ? formatValue(seg.value, unit) : formatValue(layout.total, unit)}
      </text>
      <text x={center} y={center + 14} class="c-cap">
        {seg ? `${Math.round(seg.pct)}%` : 'total'}
      </text>
    </svg>
    <ul class="legend">
      {#each layout.segments as s, i (s.label)}
        <li
          class:active={active === i}
          role="img"
          aria-label="{s.label}: {formatValue(s.value, unit)} ({Math.round(s.pct)}%)"
          onpointerenter={(e) => atPointer(e, i)}
          onpointermove={(e) => atPointer(e, i)}
          onpointerleave={() => (active = -1)}
          onpointerdown={(e) => atPointer(e, i)}
        >
          <span class="swatch" style:background={s.color}></span>
          <span class="lbl">{s.label}</span>
          <span class="val">{formatValue(s.value, unit)}{#if unit !== '%'} &middot; {Math.round(s.pct)}%{/if}</span>
        </li>
      {/each}
    </ul>
    <ChartTip
      x={tip.x}
      y={tip.y}
      show={active >= 0}
      label={seg?.label ?? ''}
      value={seg ? formatValue(seg.value, unit) : ''}
      pct={seg && unit !== '%' ? Math.round(seg.pct) : null}
    />
  </div>
{/if}

<style>
  .donut {
    display: flex;
    gap: 1.1rem;
    align-items: center;
    flex-wrap: wrap;
  }
  .chart-host {
    position: relative;
  }
  svg {
    width: 168px;
    height: 168px;
    flex: 0 0 auto;
  }
  .seg {
    cursor: pointer;
    transition: stroke-width 0.12s, opacity 0.15s;
  }
  .seg.dim {
    opacity: 0.45;
  }
  .c-val {
    text-anchor: middle;
    font-family: var(--font-head, sans-serif);
    font-weight: 700;
    font-size: 17px;
    fill: var(--civic-blue, #2c57a0);
  }
  .c-cap {
    text-anchor: middle;
    font-size: 10px;
    fill: #777;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .legend {
    list-style: none;
    margin: 0;
    padding: 0;
    min-width: 0;
    flex: 1 1 200px;
  }
  .legend li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.2rem 0.3rem;
    font-size: 0.86rem;
    border-radius: 5px;
    cursor: pointer;
  }
  .legend li:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .legend li.active {
    background: var(--civic-blue-soft, #d7e1f3);
  }
  .swatch {
    width: 0.8rem;
    height: 0.8rem;
    border-radius: 3px;
    flex: 0 0 auto;
  }
  .lbl {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .val {
    color: #555;
    white-space: nowrap;
  }
  .nodata {
    color: #888;
    font-size: 0.9rem;
    font-style: italic;
  }
</style>
