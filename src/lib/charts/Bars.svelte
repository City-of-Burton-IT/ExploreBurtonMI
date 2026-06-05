<script lang="ts">
  import type { InfoSeriesItem } from '../types';
  import { barRows, formatValue } from './scale';

  let { series, unit = '' }: { series: InfoSeriesItem[]; unit?: string } = $props();

  const rows = $derived(barRows(series));
</script>

{#if rows.length === 0}
  <p class="nodata">No data available.</p>
{:else}
  <ul class="bars">
    {#each rows as row (row.label)}
      <li>
        <div class="row-head">
          <span class="lbl">{row.label}</span>
          <span class="val">{formatValue(row.value, unit)}</span>
        </div>
        <div class="track" role="img" aria-label="{row.label}: {formatValue(row.value, unit)}">
          <div class="fill" style:width="{row.pct}%" style:background={row.color}></div>
        </div>
      </li>
    {/each}
  </ul>
{/if}

<style>
  .bars {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .bars li {
    margin: 0 0 0.7rem;
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
    color: #555;
    font-weight: 600;
    white-space: nowrap;
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
  }
  .nodata {
    color: #888;
    font-size: 0.9rem;
    font-style: italic;
  }
</style>
