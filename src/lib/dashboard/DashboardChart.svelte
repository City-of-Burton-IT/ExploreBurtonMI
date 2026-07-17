<script lang="ts">
  import type { InfoChart } from './infoPanel';
  import { csvSlug, downloadCsv } from '../csv';
  import { chartToTable } from '../panelCsv';
  import Bars from '../charts/Bars.svelte';
  import CompareBars from '../charts/CompareBars.svelte';
  import Donut from '../charts/Donut.svelte';
  import TrendLine from '../charts/TrendLine.svelte';

  let { chart }: { chart: InfoChart } = $props();

  function unreachable(value: never): never {
    throw new Error(`Unsupported dashboard chart type: ${String(value)}`);
  }

  function chartKind(value: InfoChart): InfoChart['type'] {
    switch (value.type) {
      case 'donut':
      case 'bars':
      case 'trend':
      case 'compare':
        return value.type;
      default:
        return unreachable(value.type);
    }
  }

  const kind = $derived(chartKind(chart));
  const table = $derived(chartToTable(chart));

  function exportChart(): void {
    if (!table) return;
    downloadCsv(csvSlug(chart.title), table.headers, table.rows);
  }
</script>

<figure class="chart">
  <figcaption>{chart.title}</figcaption>
  {#if kind === 'donut'}
    <Donut series={chart.series ?? []} unit={chart.unit} />
  {:else if kind === 'bars'}
    <Bars series={chart.series ?? []} unit={chart.unit} />
  {:else if kind === 'trend'}
    <TrendLine
      points={chart.points ?? []}
      unit={chart.unit}
      markers={chart.markers}
      lines={chart.lines}
    />
  {:else if kind === 'compare'}
    <CompareBars rows={chart.rows ?? []} citiesLede={chart.citiesLede} />
  {/if}
  {#if table}
    <details class="data-table">
      <summary>View data table</summary>
      <table>
        <caption class="sr-only">{chart.title}</caption>
        <thead>
          <tr>{#each table.headers as header}<th scope="col">{header}</th>{/each}</tr>
        </thead>
        <tbody>
          {#each table.rows as row}
            <tr>
              <th scope="row">{row[0]}</th>
              {#each row.slice(1) as cell}<td>{cell}</td>{/each}
            </tr>
          {/each}
        </tbody>
      </table>
      <button class="csv-btn" type="button" onclick={exportChart}>Download CSV</button>
    </details>
  {/if}
</figure>

<style>
  .chart {
    margin: 0;
    min-width: 0;
  }
  figcaption {
    font-family: var(--font-head, sans-serif);
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--civic-blue, #2c57a0);
    margin-bottom: 0.7rem;
    padding-left: 0.5rem;
    border-left: 3px solid var(--civic-blue, #2c57a0);
  }
  .data-table {
    margin-top: 0.6rem;
  }
  .data-table > summary {
    font-size: 0.78rem;
    color: var(--civic-blue-link, #1a4b8f);
    cursor: pointer;
    width: fit-content;
  }
  .data-table > summary:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: 4px;
  }
  .data-table table {
    border-collapse: collapse;
    margin-top: 0.5rem;
    font-size: 0.8rem;
    width: 100%;
  }
  .data-table th,
  .data-table td {
    text-align: left;
    padding: 0.28rem 0.6rem 0.28rem 0;
    border-bottom: 1px solid var(--pub-border, #e3e3e3);
    white-space: nowrap;
  }
  .data-table thead th {
    color: var(--pub-muted, #5c5c5c);
    font-weight: 700;
  }
  .data-table tbody th {
    font-weight: 600;
    white-space: normal;
  }
  .data-table td {
    font-variant-numeric: tabular-nums;
  }
  .csv-btn {
    margin-top: 0.6rem;
    border: 1px solid var(--civic-blue, #2c57a0);
    background: var(--pub-surface);
    color: var(--civic-blue, #2c57a0);
    border-radius: var(--pub-radius-sm, 8px);
    padding: 0.3rem 0.7rem;
    font-family: var(--font-body, sans-serif);
    font-weight: 700;
    font-size: 0.76rem;
    cursor: pointer;
  }
  .csv-btn:hover {
    background: var(--civic-blue-soft, #d7e1f3);
  }
  .csv-btn:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
</style>
