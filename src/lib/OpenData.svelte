<script lang="ts">
  import type { InfoPanel } from './types';
  import { DASHBOARD_GROUPS } from './store.svelte';
  import { formatDataAsOf } from './freshness';
  import { csvSlug, downloadCsvText } from './csv';
  import { panelToCsv } from './panelCsv';
  import { safeHref } from './templates';

  // One transparency index for every dashboard dataset: source, vintage
  // ("Data as of"), and a single combined CSV download (stats + every chart +
  // every table), reusing the same csv helpers as the per-chart exports (#63).
  let { panels, loading }: { panels: Record<string, InfoPanel | null>; loading: boolean } = $props();

  function download(id: string, label: string): void {
    const panel = panels[id];
    if (!panel) return;
    const csv = panelToCsv(panel);
    if (!csv) return;
    downloadCsvText(`${csvSlug(label)}-burton`, csv);
  }

  // A dataset is downloadable when its panel loaded and has at least one tabular
  // section. Recomputed from the live panels map.
  function hasData(id: string): boolean {
    const panel = panels[id];
    return !!panel && panelToCsv(panel).length > 0;
  }
</script>

<section class="opendata" aria-label="Open Data downloads">
  <header class="intro">
    <h2>Open Data</h2>
    <p>
      Every dashboard on this site is built from public data. Download any dataset below as a
      CSV (spreadsheet) file: the same numbers shown on the dashboard, with its source and
      the date it was last refreshed. No account needed.
    </p>
  </header>

  {#if loading}
    <p class="state">Loading datasets&hellip;</p>
  {:else}
    {#each DASHBOARD_GROUPS as group (group.label)}
      <h3 class="group">{group.label}</h3>
      <ul class="datasets">
        {#each group.items as item (item.id)}
          {@const panel = panels[item.id]}
          {@const asOf = formatDataAsOf(panel?.lastUpdated)}
          <li class="dataset">
            <div class="meta">
              <span class="name">{item.label}</span>
              <span class="src">
                {#if panel?.source}{panel.source}{:else}Source listed on the dashboard{/if}
                {#if asOf} &middot; {asOf}{/if}
              </span>
            </div>
            {#if hasData(item.id)}
              <button class="dl" onclick={() => download(item.id, item.label)}>
                <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor"
                  stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"
                  ><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line
                    x1="12" x2="12" y1="15" y2="3" /></svg
                >
                CSV
              </button>
            {:else}
              <span class="unavail">Unavailable</span>
            {/if}
          </li>
        {/each}
      </ul>
    {/each}
    <p class="foot">
      Looking for the map data (businesses, facilities, boundaries)? See the
      <a href={safeHref('https://github.com/City-of-Burton-IT/ExploreBurtonMI')} target="_blank" rel="noopener noreferrer">project repository</a>.
      Each dashboard also has per-chart CSV downloads.
    </p>
  {/if}
</section>

<style>
  .opendata {
    height: 100%;
    overflow-y: auto;
    background: var(--pub-surface);
    padding: 1.2rem 1.4rem 2rem;
  }
  .intro {
    max-width: 60ch;
  }
  h2 {
    margin: 0 0 0.4rem;
    font-family: var(--font-head);
    font-weight: 700;
    color: var(--civic-blue);
    font-size: 1.5rem;
  }
  .intro p {
    margin: 0;
    color: var(--pub-ink);
    line-height: 1.5;
  }
  .state {
    color: var(--pub-muted, #5c5c5c);
  }
  .group {
    margin: 1.6rem 0 0.5rem;
    font-family: var(--font-head);
    font-weight: 700;
    font-size: 1rem;
    color: var(--civic-blue-deep, #1e437e);
    border-bottom: 1px solid var(--pub-border, #e3e3e3);
    padding-bottom: 0.3rem;
  }
  .datasets {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .dataset {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.6rem 0;
    border-bottom: 1px solid var(--pub-border-soft);
  }
  .meta {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .name {
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--pub-ink);
  }
  .src {
    font-size: 0.8rem;
    color: var(--pub-muted, #5c5c5c);
  }
  .dl {
    flex: none;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border: 1px solid var(--civic-blue);
    border-radius: 999px;
    background: none;
    color: var(--civic-blue);
    font-family: var(--font-body);
    font-size: 0.82rem;
    font-weight: 700;
    padding: 0.35rem 0.8rem;
    cursor: pointer;
    transition: background var(--motion-duration), color var(--motion-duration);
  }
  .dl:hover {
    background: var(--civic-accent-bg);
    color: #fff;
  }
  .dl:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .unavail {
    flex: none;
    font-size: 0.8rem;
    color: var(--pub-muted, #5c5c5c);
  }
  .foot {
    margin-top: 1.4rem;
    font-size: 0.85rem;
    color: var(--pub-muted, #5c5c5c);
    max-width: 60ch;
  }
  .foot a {
    color: var(--civic-blue-link);
  }
</style>
