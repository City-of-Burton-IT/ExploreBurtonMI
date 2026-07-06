<script lang="ts">
  import type { InfoSeriesItem } from '../types';
  import { barRows, formatValue } from './scale';
  import { createChartHover } from './chartHover.svelte';
  import ChartTip from './ChartTip.svelte';

  let { series, unit = '' }: { series: InfoSeriesItem[]; unit?: string } = $props();

  const rows = $derived(barRows(series));
  const total = $derived(rows.reduce((s, r) => s + (r.value > 0 ? r.value : 0), 0));

  const hover = createChartHover(-1);
  const active = $derived(hover.active);
  const shareOfTotal = (v: number) => (total > 0 ? Math.round((Math.max(v, 0) / total) * 100) : 0);
</script>

{#if rows.length === 0}
  <p class="nodata">No data available.</p>
{:else}
  <div class="chart-host" bind:this={hover.host}>
    <ul class="bars" class:has-active={active >= 0}>
      {#each rows as row, i (row.label)}
        <li
          class:active={active === i}
          role="img"
          aria-label="{row.label}: {formatValue(row.value, unit)} ({shareOfTotal(row.value)}% of total)"
          onpointerenter={(e) => hover.atPointer(e, i)}
          onpointermove={(e) => hover.atPointer(e, i)}
          onpointerleave={() => hover.clear()}
          onpointerdown={(e) => hover.atPointer(e, i)}
        >
          <div class="row-head">
            <span class="lbl">{row.label}</span>
            <span class="val">{formatValue(row.value, unit)}</span>
          </div>
          <div class="track">
            <div class="fill" style:width="{row.pct}%" style:background={row.color}></div>
          </div>
        </li>
      {/each}
    </ul>
    <ChartTip
      x={hover.tip.x}
      y={hover.tip.y}
      show={active >= 0}
      label={rows[active]?.label ?? ''}
      value={active >= 0 ? formatValue(rows[active].value, unit) : ''}
      pct={active >= 0 && unit !== '%' ? shareOfTotal(rows[active].value) : null}
    />
  </div>
{/if}

<style>
  .chart-host {
    position: relative;
  }
  .bars {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .bars li {
    margin: 0 0 0.7rem;
    cursor: pointer;
    border-radius: 6px;
    transition: opacity var(--motion-duration);
  }
  .bars li:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  /* Dim the rest while one row is hovered/focused. */
  .bars.has-active li:not(.active) {
    opacity: 0.5;
  }
  .row-head {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    font-size: 0.86rem;
    margin-bottom: 0.2rem;
  }
  .lbl {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .val {
    color: var(--pub-muted);
    font-weight: 600;
    white-space: nowrap;
  }
  .active .val {
    color: var(--civic-blue, #2c57a0);
  }
  .track {
    background: #eef1f5;
    border-radius: 999px;
    height: 0.7rem;
    overflow: hidden;
  }
  .fill {
    height: 100%;
    border-radius: 999px;
    min-width: 2px;
    transition: filter var(--motion-duration);
  }
  .active .fill {
    filter: brightness(1.08) saturate(1.1);
  }
  .nodata {
    color: var(--pub-muted, #5c5c5c);
    font-size: 0.9rem;
    font-style: italic;
  }
</style>
