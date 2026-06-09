<script lang="ts">
  import type { InfoTable } from './types';

  let { table }: { table: InfoTable } = $props();
</script>

<figure class="info-table">
  <figcaption>{table.title}</figcaption>
  <!-- Horizontal scroll on narrow screens so a wide table never blows out the panel. -->
  <div class="scroll">
    <table>
      <thead>
        <tr>
          {#each table.columns as col (col)}
            <th scope="col">{col}</th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each table.rows as row, i (i)}
          <tr>
            {#each row.cells as cell, c (c)}
              <!-- Svelte auto-escapes {cell}; the color dot is decorative (condition
                   is also a text column, so color is never the sole signal). -->
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
    font-family: var(--font-head, sans-serif);
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--civic-blue, #2c57a0);
    margin-bottom: 0.7rem;
    padding-left: 0.5rem;
    border-left: 3px solid var(--civic-blue, #2c57a0);
  }
  .scroll {
    overflow-x: auto;
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
  th {
    color: var(--civic-blue, #2c57a0);
    font-weight: 700;
    border-bottom: 2px solid var(--civic-blue, #2c57a0);
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
