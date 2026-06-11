<script lang="ts">
  import type { InfoTable } from './types';
  import { sortRows } from './tableSort';
  import { csvSlug, downloadCsv } from './csv';

  let { table }: { table: InfoTable } = $props();

  let sortCol = $state<number | null>(null);
  let sortDir = $state<'asc' | 'desc'>('asc');

  const displayRows = $derived(
    sortCol === null ? table.rows : sortRows(table.rows, sortCol, sortDir),
  );

  function sortBy(col: number) {
    if (sortCol === col) {
      sortDir = sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      sortCol = col;
      sortDir = 'asc';
    }
  }
  function ariaSort(col: number): 'ascending' | 'descending' | 'none' {
    if (sortCol !== col) return 'none';
    return sortDir === 'asc' ? 'ascending' : 'descending';
  }
  function exportCsv() {
    downloadCsv(
      csvSlug(table.title),
      table.columns,
      displayRows.map((r) => r.cells),
    );
  }
</script>

<figure class="info-table">
  <figcaption>
    <span class="cap">{table.title}</span>
    <button class="csv-btn" type="button" onclick={exportCsv}>Download CSV</button>
  </figcaption>
  <!-- Vertical + horizontal scroll so a long/wide table scrolls inside its own
       region and the header row stays stuck to the top while you scroll. -->
  <div class="scroll">
    <table>
      <thead>
        <tr>
          {#each table.columns as col, c (col)}
            <th scope="col" aria-sort={ariaSort(c)}>
              <button class="sort" type="button" onclick={() => sortBy(c)}>
                {col}<span class="arrow" aria-hidden="true"
                  >{sortCol === c ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''}</span
                >
              </button>
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each displayRows as row, i (i)}
          <tr>
            {#each row.cells as cell, c (c)}
              <!-- Svelte auto-escapes {cell}; the color dot is decorative (the
                   first column is also text, so color is never the sole signal). -->
              <td>
                {#if c === 0 && row.color}
                  <span class="dot" style:background={row.color} aria-hidden="true"></span>
                {/if}{cell}
              </td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</figure>

<style>
  .info-table {
    margin: 0;
    min-width: 0;
  }
  figcaption {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.7rem;
    font-family: var(--font-head, sans-serif);
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--civic-blue, #2c57a0);
    margin-bottom: 0.7rem;
    padding-left: 0.5rem;
    border-left: 3px solid var(--civic-blue, #2c57a0);
  }
  .csv-btn {
    flex: 0 0 auto;
    border: none;
    background: none;
    color: var(--civic-blue-link, #386fc5);
    font-family: var(--font-body, sans-serif);
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    padding: 0;
  }
  .csv-btn:hover {
    text-decoration: underline;
  }
  .csv-btn:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: var(--pub-radius-sm, 8px);
  }
  .scroll {
    overflow: auto;
    max-height: 420px;
    -webkit-overflow-scrolling: touch;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    font-size: 0.82rem;
  }
  th,
  td {
    text-align: left;
    padding: 0.4rem 0.7rem;
    border-bottom: 1px solid #e7ebf0;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
  /* Header sticks to the top of the scroll region; needs a solid background so
     scrolled rows don't show through. */
  thead th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: var(--civic-blue-soft, #d7e1f3);
    color: var(--civic-blue-deep, #1e437e);
    font-weight: 700;
    border-bottom: 2px solid var(--civic-blue, #2c57a0);
  }
  .sort {
    display: inline-flex;
    align-items: center;
    border: none;
    background: none;
    font: inherit;
    color: inherit;
    font-weight: 700;
    cursor: pointer;
    padding: 0;
    white-space: nowrap;
  }
  .sort:hover {
    text-decoration: underline;
  }
  .sort:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: var(--pub-radius-sm, 6px);
  }
  .arrow {
    font-size: 0.7em;
  }
  tbody tr:nth-child(even) {
    background: #f7f9fb;
  }
  .dot {
    display: inline-block;
    width: 0.62rem;
    height: 0.62rem;
    border-radius: 999px;
    margin-right: 0.45rem;
    vertical-align: baseline;
    border: 1px solid rgba(0, 0, 0, 0.15);
  }
</style>
