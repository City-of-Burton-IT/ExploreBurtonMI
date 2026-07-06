<script lang="ts">
  import { loadJson } from '../loadJson.svelte';
  import OfflineBadge from '../OfflineBadge.svelte';

  type Entry = { street: string; day: string };

  const schedule = loadJson<Entry[]>(
    'waste-schedule.json',
    (raw) => (raw as { entries?: Entry[] }).entries ?? [],
    [],
  );
  const entries = $derived(schedule.data);
  const loading = $derived(schedule.loading);
  let query = $state('');

  const DAY_COLORS: Record<string, string> = {
    Monday: '#1565c0',
    Tuesday: '#2e7d32',
    Wednesday: '#e65100',
    Thursday: '#6a1b9a',
    Friday: '#00838f',
  };
  const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];

  const q = $derived(query.trim().toLowerCase());
  const matches = $derived(
    q.length === 0 ? [] : entries.filter((e) => e.street.toLowerCase().includes(q)),
  );
  const shown = $derived(matches.slice(0, 60));
</script>

<div class="waste">
  <OfflineBadge label="Offline: showing your saved pickup schedule" />
  <p class="intro">
    Garbage, recycling, and yard waste are all collected on the <strong>same day</strong>, out by
    <strong>6:00 a.m.</strong> Type your street below to find your pickup day. When a holiday falls on or
    before your day, collection that week is delayed one day.
  </p>

  <label class="search">
    <span class="sr-only">Search your street</span>
    <input
      type="search"
      placeholder="Start typing your street&hellip; (e.g. Belsay, Maple)"
      bind:value={query}
      autocomplete="off"
    />
  </label>

  {#if loading}
    <p class="state">Loading the schedule&hellip;</p>
  {:else if entries.length === 0}
    <p class="state">The schedule is temporarily unavailable. Please check back soon.</p>
  {:else if q.length === 0}
    <p class="hint">Showing {entries.length} streets. Start typing to find yours.</p>
  {:else if matches.length === 0}
    <p class="hint">No street matches &ldquo;{query}&rdquo;. Try a shorter search, or call Emterra at (810) 667-4885.</p>
  {:else}
    <ul class="results">
      {#each shown as e (e.street + e.day)}
        <li>
          <span class="street">{e.street}</span>
          <span class="chip" style:background={DAY_COLORS[e.day] ?? '#555'}>{e.day}</span>
        </li>
      {/each}
    </ul>
    {#if matches.length > shown.length}
      <p class="hint">Showing the first {shown.length} of {matches.length} matches. Keep typing to narrow it down.</p>
    {/if}
  {/if}

  <div class="legend" aria-hidden="true">
    {#each DAYS as d (d)}
      <span class="legend-item"><span class="dot" style:background={DAY_COLORS[d]}></span>{d}</span>
    {/each}
  </div>

  <p class="note">
    Source: City of Burton Waste Removal Schedule (hauler: Emterra). Streets spanning multiple areas may
    list more than one segment. Questions? Call Emterra at <a href="tel:+18106674885">(810) 667-4885</a>.
  </p>
</div>

<style>
  .waste {
    max-width: 640px;
  }
  .intro {
    line-height: 1.6;
    margin: 0 0 1rem;
  }
  .search input {
    width: 100%;
    box-sizing: border-box;
    padding: 0.7rem 0.9rem;
    font-size: 1rem;
    border: 2px solid var(--pub-border, #d8dde4);
    border-radius: var(--pub-radius, 10px);
    font-family: var(--font-body, sans-serif);
  }
  .search input:focus-visible {
    outline: none;
    border-color: var(--civic-blue, #2c57a0);
    box-shadow: var(--pub-focus-ring);
  }
  .state,
  .hint {
    color: var(--pub-muted, #5c5c5c);
    font-size: 0.9rem;
    margin: 0.8rem 0;
  }
  .results {
    list-style: none;
    margin: 0.9rem 0 0;
    padding: 0;
    border-top: 1px solid var(--pub-border, #e3e3e3);
  }
  .results li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.8rem;
    padding: 0.5rem 0.2rem;
    border-bottom: 1px solid var(--pub-border, #eef1f5);
  }
  .street {
    min-width: 0;
  }
  .chip {
    flex: 0 0 auto;
    color: #fff;
    font-weight: 700;
    font-size: 0.78rem;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    white-space: nowrap;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
    margin: 1.1rem 0 0;
    font-size: 0.8rem;
    color: var(--pub-muted);
  }
  .legend-item {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }
  .dot {
    width: 0.7rem;
    height: 0.7rem;
    border-radius: 50%;
    display: inline-block;
  }
  .note {
    margin: 1.2rem 0 0;
    font-size: 0.78rem;
    color: var(--pub-muted, #5c5c5c);
    line-height: 1.4;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
  }
</style>
