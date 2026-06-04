<script lang="ts">
  import { loadConfig } from './lib/config';
  import { loadData } from './lib/data';
  import { filterFeatures } from './lib/filter';
  import { buildIndex, searchIds } from './lib/search';
  import type { AppConfig, PlaceCollection } from './lib/types';
  import { ui, setMobileView, openAbout } from './lib/store.svelte';
  import Map from './lib/Map.svelte';
  import Detail from './lib/Detail.svelte';
  import Facets from './lib/Facets.svelte';
  import List from './lib/List.svelte';
  import Search from './lib/Search.svelte';
  import About from './lib/About.svelte';

  let config = $state<AppConfig | null>(null);
  let data = $state<PlaceCollection | null>(null);
  let error = $state<string | null>(null);

  async function start() {
    const cfg = await loadConfig();
    config = cfg;
    data = await loadData(cfg.data.source);
  }

  start().catch((e) => (error = e instanceof Error ? e.message : String(e)));

  const index = $derived(
    config && data ? buildIndex(data.features, config.search.keys) : null,
  );
  const matchedIds = $derived(index ? searchIds(index, ui.query) : null);

  const result = $derived(
    config && data
      ? filterFeatures(data.features, config.facets, ui.selections, (f) =>
          matchedIds ? matchedIds.has(f.id) : true,
        )
      : null,
  );
  const filteredIds = $derived(new Set(result?.filteredIds ?? []));
  const filteredFeatures = $derived(
    data ? data.features.filter((f) => filteredIds.has(f.id)) : [],
  );
</script>

<div class="app">
  <header class="topbar">
    <img class="seal" src="/burton-seal.png" alt="City of Burton seal" width="44" height="44" />
    <div class="brand">
      <h1>{config?.project.name ?? 'Explore Burton'}</h1>
      {#if config?.project.tagline}
        <p class="tagline">{config.project.tagline}</p>
      {/if}
    </div>
    {#if config}
      <span class="spacer"></span>
      {#if data && result}
        <div class="view-toggle" role="group" aria-label="Switch between map and list">
          <button class:active={ui.mobileView === 'map'} onclick={() => setMobileView('map')}>Map</button>
          <button class:active={ui.mobileView === 'list'} onclick={() => setMobileView('list')}>List</button>
        </div>
      {/if}
      <a class="home-btn" href="https://www.burtonmi.gov">Home</a>
      <About {config} />
    {/if}
  </header>

  {#if error}
    <div class="status error" role="alert">
      <strong>Could not start the map.</strong>
      <pre>{error}</pre>
    </div>
  {:else if config && data && result}
    <div class="workspace" data-view={ui.mobileView}>
      <aside class="sidebar">
        <Search />
        <Facets {config} facetCounts={result.facetCounts} />
        <List {config} features={filteredFeatures} />
      </aside>
      <main class="content">
        <Map {config} {data} {filteredIds} />
        <Detail {config} />
        <button
          class="map-credit"
          onclick={openAbout}
          title="Map credits & about"
          aria-label="Map credits and about this map"
        >&copy;</button>
      </main>
    </div>
  {:else}
    <div class="status">Loading&hellip;</div>
  {/if}
</div>
