<script lang="ts">
  import type { CompareRow } from '../types';
  import { formatValue } from './scale';

  let { rows }: { rows: CompareRow[] } = $props();

  // The first place (Burton) is the subject and is emphasised; the rest are
  // muted reference bars (county, state).
  const SUBJECT = '#2c57a0'; // civic blue
  const REF = ['#9bb4cf', '#c5d2dd']; // muted blues for county / state

  function colorFor(i: number): string {
    return i === 0 ? SUBJECT : REF[(i - 1) % REF.length];
  }
  function pct(value: number, max: number): number {
    return max > 0 ? (Math.max(value, 0) / max) * 100 : 0;
  }
</script>

{#if rows.length === 0}
  <p class="nodata">No data available.</p>
{:else}
  <div class="compare">
    {#each rows as row (row.label)}
      {@const max = Math.max(...row.values.map((v) => (v.value > 0 ? v.value : 0)), 0)}
      <div class="metric">
        <div class="metric-label">{row.label}</div>
        {#each row.values as v, i (v.name)}
          <div class="cmp-row" class:subject={i === 0}>
            <span class="place">{v.name}</span>
            <span class="track">
              <span class="fill" style:width="{pct(v.value, max)}%" style:background={colorFor(i)}></span>
            </span>
            <span class="num">{formatValue(v.value, row.unit ?? '')}</span>
          </div>
        {/each}
      </div>
    {/each}
  </div>
{/if}

<style>
  .compare {
    display: grid;
    gap: 1rem;
  }
  .metric-label {
    font-size: 0.86rem;
    font-weight: 700;
    color: var(--pub-ink, #2c2c2c);
    margin-bottom: 0.3rem;
  }
  .cmp-row {
    display: grid;
    grid-template-columns: 6.5rem 1fr auto;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8rem;
    margin: 0.18rem 0;
  }
  .place {
    color: #666;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .subject .place {
    color: var(--civic-blue, #2c57a0);
    font-weight: 700;
  }
  .track {
    background: #eef1f5;
    border-radius: 999px;
    height: 0.6rem;
    overflow: hidden;
  }
  .fill {
    display: block;
    height: 100%;
    border-radius: 999px;
    min-width: 2px;
  }
  .num {
    white-space: nowrap;
    color: #555;
    font-variant-numeric: tabular-nums;
  }
  .subject .num {
    color: var(--civic-blue, #2c57a0);
    font-weight: 700;
  }
  .nodata {
    color: #888;
    font-size: 0.9rem;
    font-style: italic;
  }
</style>
