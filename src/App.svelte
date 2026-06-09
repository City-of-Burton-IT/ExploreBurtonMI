<script lang="ts">
  import { onMount } from 'svelte';
  import { loadConfig } from './lib/config';
  import { loadData } from './lib/data';
  import { filterFeatures } from './lib/filter';
  import { buildIndex, searchIds } from './lib/search';
  import type { AppConfig, PlaceCollection, InfoPanel } from './lib/types';
  import { ui, setMobileView, setView, syncViewFromHash, openAbout, isDashboard, DASHBOARDS } from './lib/store.svelte';
  import Map from './lib/Map.svelte';
  import Detail from './lib/Detail.svelte';
  import Facets from './lib/Facets.svelte';
  import List from './lib/List.svelte';
  import Search from './lib/Search.svelte';
  import About from './lib/About.svelte';
  import InfoView from './lib/InfoView.svelte';
  import Guide from './lib/Guide.svelte';
  import DashboardMenu from './lib/DashboardMenu.svelte';
  import InstallPrompt from './lib/InstallPrompt.svelte';

  let config = $state<AppConfig | null>(null);
  let data = $state<PlaceCollection | null>(null);
  let error = $state<string | null>(null);

  // Info panels load independently of the map and never block or break it.
  // Keyed by view id so the nav + activePanel lookup stay in sync with the
  // DASHBOARDS list (one place to add a dashboard).
  let panels = $state<Record<string, InfoPanel | null>>({});
  let infoLoading = $state(true);

  async function start() {
    const cfg = await loadConfig();
    config = cfg;
    data = await loadData(cfg.data.source);
  }

  async function loadInfo() {
    const safe = (url: string): Promise<InfoPanel | null> =>
      fetch(url)
        .then((r) => (r.ok ? (r.json() as Promise<InfoPanel>) : null))
        .catch(() => null);
    // Derive from DASHBOARDS (single source of truth) so a new dashboard added
    // there is fetched automatically -- never hardcode this list (it silently
    // dropped newly-added panels before).
    const ids = DASHBOARDS.map((d) => d.id);
    const loaded = await Promise.all(ids.map((id) => safe(`info-${id}.json`)));
    panels = Object.fromEntries(ids.map((id, i) => [id, loaded[i]]));
    infoLoading = false;
  }

  start().catch((e) => (error = e instanceof Error ? e.message : String(e)));
  loadInfo();

  onMount(() => {
    window.addEventListener('hashchange', syncViewFromHash);
    return () => window.removeEventListener('hashchange', syncViewFromHash);
  });

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

  // Great-circle distance (m) between two [lat,lng] points, for "Near me" sorting.
  function haversine(aLat: number, aLng: number, bLat: number, bLng: number): number {
    const R = 6371000;
    const dLat = ((bLat - aLat) * Math.PI) / 180;
    const dLng = ((bLng - aLng) * Math.PI) / 180;
    const s =
      Math.sin(dLat / 2) ** 2 +
      Math.cos((aLat * Math.PI) / 180) * Math.cos((bLat * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(s));
  }

  const filteredFeatures = $derived.by(() => {
    if (!data) return [];
    const feats = data.features.filter((f) => filteredIds.has(f.id));
    const loc = ui.userLocation;
    if (!loc) return feats;
    // Nearest-first once the user shares their location.
    return [...feats].sort((a, b) => {
      const [aLng, aLat] = a.geometry.coordinates;
      const [bLng, bLat] = b.geometry.coordinates;
      return haversine(loc.lat, loc.lng, aLat, aLng) - haversine(loc.lat, loc.lng, bLat, bLng);
    });
  });

  const activePanel = $derived(isDashboard(ui.view) ? (panels[ui.view] ?? null) : null);
</script>

<div class="app">
  <header class="topbar">
    <a class="seal-link" href="https://www.burtonmi.gov" aria-label="City of Burton home page">
      <img class="seal" src="/burton-seal.png" alt="City of Burton seal" width="44" height="44" />
    </a>
    <div class="brand">
      <h1>{config?.project.name ?? 'Explore Burton'}</h1>
      {#if config?.project.tagline}
        <p class="tagline">{config.project.tagline}</p>
      {/if}
    </div>
    {#if config}
      <span class="spacer"></span>
      <nav class="viewnav" aria-label="Sections">
        <button class:active={ui.view === 'map'} onclick={() => setView('map')}>Map</button>
        <DashboardMenu />
        <button class:active={ui.view === 'guide'} onclick={() => setView('guide')}><span class="rg-prefix">Resident </span>Guide</button>
      </nav>
      {#if data && result && ui.view === 'map'}
        <div class="view-toggle" role="group" aria-label="Switch between map and list">
          <button class:active={ui.mobileView === 'map'} onclick={() => setMobileView('map')}>Map</button>
          <button class:active={ui.mobileView === 'list'} onclick={() => setMobileView('list')}>List</button>
        </div>
      {/if}
      <a class="home-btn" href="https://www.burtonmi.gov">Home</a>
      <!-- Trigger lives at the end of the Guide; this keeps the dialog mounted so
           the map © button (and the Guide's About button) can open it. -->
      <About {config} showButton={false} />
    {/if}
  </header>

  {#if error}
    <div class="status error" role="alert">
      <strong>Could not start the map.</strong>
      <pre>{error}</pre>
    </div>
  {:else if config && data && result}
    <div class="workspace" data-view={ui.mobileView} class:hidden={ui.view !== 'map'}>
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
    {#if isDashboard(ui.view)}
      <div class="infowrap">
        <InfoView panel={activePanel} loading={infoLoading} />
      </div>
    {:else if ui.view === 'guide'}
      <div class="infowrap">
        <Guide />
      </div>
    {/if}
  {:else}
    <div class="status">Loading&hellip;</div>
  {/if}

  <InstallPrompt />
</div>
