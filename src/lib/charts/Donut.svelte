<script lang="ts">
  import type { InfoSeriesItem } from '../types';
  import { donutSegments, formatValue } from './scale';

  let { series, unit = '' }: { series: InfoSeriesItem[]; unit?: string } = $props();

  const SIZE = 168;
  const R = 60;
  const STROKE = 26;
  const center = SIZE / 2;

  const layout = $derived(donutSegments(series, R));
</script>

{#if layout.segments.length === 0}
  <p class="nodata">No data available.</p>
{:else}
  <div class="donut">
    <svg viewBox="0 0 {SIZE} {SIZE}" role="img" aria-label="Proportional breakdown">
      <g transform="rotate(-90 {center} {center})">
        {#each layout.segments as seg (seg.label)}
          <circle
            cx={center}
            cy={center}
            r={R}
            fill="none"
            stroke={seg.color}
            stroke-width={STROKE}
            stroke-dasharray="{seg.dash} {seg.gap}"
            stroke-dashoffset={-seg.offset}
          >
            <title>{seg.label}: {formatValue(seg.value, unit)}{#if unit !== '%'} ({Math.round(seg.pct)}%){/if}</title>
          </circle>
        {/each}
      </g>
    </svg>
    <ul class="legend">
      {#each layout.segments as seg (seg.label)}
        <li>
          <span class="swatch" style:background={seg.color}></span>
          <span class="lbl">{seg.label}</span>
          <span class="val">{formatValue(seg.value, unit)}{#if unit !== '%'} · {Math.round(seg.pct)}%{/if}</span>
        </li>
      {/each}
    </ul>
  </div>
{/if}

<style>
  .donut {
    display: flex;
    gap: 1.1rem;
    align-items: center;
    flex-wrap: wrap;
  }
  svg {
    width: 168px;
    height: 168px;
    flex: 0 0 auto;
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
    padding: 0.2rem 0;
    font-size: 0.86rem;
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
