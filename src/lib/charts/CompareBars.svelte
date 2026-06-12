<script lang="ts">
  import type { CompareRow, CompareValue } from '../types';
  import { formatValue, CIVIC_BLUE } from './scale';

  let { rows, citiesLede }: { rows: CompareRow[]; citiesLede?: string } = $props();

  // The first place (Burton) is the subject and is emphasised; the rest are
  // muted reference bars (county, state).
  const SUBJECT = CIVIC_BLUE;
  const REF = ['#9bb4cf', '#c5d2dd']; // muted blues for county / state

  // The "Burton vs county cities" toggle only appears when the data carries a
  // per-city ranking (#28). Default stays on the region comparison.
  const hasCities = $derived(rows.some((r) => (r.cities?.length ?? 0) >= 3));
  let mode = $state<'region' | 'cities'>('region');
  const showCities = $derived(hasCities && mode === 'cities');

  function colorFor(i: number): string {
    return i === 0 ? SUBJECT : REF[(i - 1) % REF.length];
  }
  function pct(value: number, max: number): number {
    return max > 0 ? (Math.max(value, 0) / max) * 100 : 0;
  }
  const isBurton = (name: string) => name === 'Burton';
  function burtonRank(cities: CompareValue[]): number {
    return cities.findIndex((c) => isBurton(c.name)) + 1;
  }
  // Cities are sorted high-to-low, so position N = "Nth highest value". Stating
  // "highest" keeps the rank unambiguous for lower-is-better metrics (poverty,
  // unemployment) without colouring them good or bad.
  function ordinal(n: number): string {
    const s = ['th', 'st', 'nd', 'rd'];
    const v = n % 100;
    return n + (s[(v - 20) % 10] ?? s[v] ?? s[0]);
  }
</script>

{#if rows.length === 0}
  <p class="nodata">No data available.</p>
{:else}
  {#if hasCities}
    <div class="cmp-toggle" role="group" aria-label="Comparison scope">
      <button class:active={mode === 'region'} onclick={() => (mode = 'region')}>Burton vs region</button>
      <button class:active={mode === 'cities'} onclick={() => (mode = 'cities')}>Genesee County cities</button>
    </div>
  {/if}

  {#if showCities && citiesLede}
    <p class="cities-lede">{citiesLede}</p>
  {/if}

  <div class="compare">
    {#each rows as row (row.label)}
      {#if showCities && row.cities}
        {@const max = Math.max(...row.cities.map((v) => (v.value > 0 ? v.value : 0)), 0)}
        {@const rank = burtonRank(row.cities)}
        <div class="metric">
          <div class="metric-label">
            {row.label}
            {#if rank > 0 && !citiesLede}<span class="rank">Burton: {ordinal(rank)} highest of {row.cities.length}</span>{/if}
          </div>
          {#each row.cities as v (v.name)}
            <div class="cmp-row" class:subject={isBurton(v.name)}>
              <span class="place">{v.name}</span>
              <span class="track">
                <span
                  class="fill"
                  style:width="{pct(v.value, max)}%"
                  style:background={isBurton(v.name) ? SUBJECT : REF[0]}
                ></span>
              </span>
              <span class="num">{formatValue(v.value, row.unit ?? '')}</span>
            </div>
          {/each}
        </div>
      {:else}
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
      {/if}
    {/each}
  </div>
{/if}

<style>
  .cmp-toggle {
    display: inline-flex;
    border: 1px solid var(--civic-blue, #2c57a0);
    border-radius: 999px;
    overflow: hidden;
    margin-bottom: 0.9rem;
  }
  .cmp-toggle button {
    border: none;
    background: #fff;
    color: var(--civic-blue, #2c57a0);
    font-family: var(--font-body, sans-serif);
    font-weight: 700;
    font-size: 0.78rem;
    padding: 0.34rem 0.8rem;
    cursor: pointer;
    transition: background var(--motion-duration), color var(--motion-duration);
  }
  .cmp-toggle button + button {
    border-left: 1px solid var(--civic-blue, #2c57a0);
  }
  .cmp-toggle button.active {
    background: var(--civic-blue, #2c57a0);
    color: #fff;
  }
  .cmp-toggle button:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .cities-lede {
    margin: 0 0 1rem;
    padding: 0.7rem 0.85rem;
    background: var(--civic-green-soft, #d9f1dd);
    border-left: 3px solid var(--civic-green, #4ea735);
    border-radius: var(--pub-radius-sm, 8px);
    font-size: 0.85rem;
    line-height: 1.5;
    color: var(--pub-ink, #2c2c2c);
  }
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
  .rank {
    margin-left: 0.5rem;
    font-size: 0.76rem;
    font-weight: 600;
    color: var(--civic-blue, #2c57a0);
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
  /* Non-colour cues so Burton reads as the subject even under colour-vision
     deficiency or in greyscale: a taller bar with a darker inset outline, on top
     of the already-bold label + value. References stay short + muted. */
  .subject .track {
    height: 0.78rem;
  }
  .subject .fill {
    box-shadow: inset 0 0 0 1.5px var(--civic-blue-deep, #1e437e);
  }
  .nodata {
    color: var(--pub-muted, #5c5c5c);
    font-size: 0.9rem;
    font-style: italic;
  }
</style>
