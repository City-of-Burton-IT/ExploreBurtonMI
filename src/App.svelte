<script lang="ts">
  import { onMount } from 'svelte';
  import { loadConfig } from './lib/config';
  import { loadData } from './lib/data';
  import { dataFetch } from './lib/remote';
  import { filterFeatures } from './lib/filter';
  import { buildIndex, searchIds } from './lib/search';
  import type { AppConfig, PlaceCollection, InfoPanel } from './lib/types';
  import { ui, setMobileView, setView, syncViewFromHash, openAbout, isDashboard, DASHBOARDS, select, clearSelection, dashboardGroupLabel, adjacentDashboards, initOnlineWatch } from './lib/store.svelte';
  import { placeIdFromHash } from './lib/hash';
  import Map from './lib/Map.svelte';
  import Detail from './lib/Detail.svelte';
  import Facets from './lib/Facets.svelte';
  import List from './lib/List.svelte';
  import Search from './lib/Search.svelte';
  import About from './lib/About.svelte';
  import InfoView from './lib/InfoView.svelte';
  import Guide from './lib/Guide.svelte';
  import OpenData from './lib/OpenData.svelte';
  import DashboardMenu from './lib/DashboardMenu.svelte';
  import InstallPrompt from './lib/InstallPrompt.svelte';
  import AlertBanner from './lib/AlertBanner.svelte';
  import WelcomeModal from './lib/WelcomeModal.svelte';
  import SuggestEdit from './lib/SuggestEdit.svelte';
  import ReportIssue from './lib/ReportIssue.svelte';
  import QuickActions from './lib/QuickActions.svelte';

  let config = $state<AppConfig | null>(null);
  let data = $state<PlaceCollection | null>(null);
  let error = $state<string | null>(null);

  // Info panels load independently of the map and never block or break it.
  // Keyed by view id so the nav + activePanel lookup stay in sync with the
  // DASHBOARDS list (one place to add a dashboard).
  let panels = $state<Record<string, InfoPanel | null>>({});
  let panelErrors = $state<Record<string, boolean>>({});
  let infoLoading = $state(true);

  async function start() {
    const cfg = await loadConfig();
    config = cfg;
    data = await loadData(cfg.data.source);
    reconcilePlace(); // honor a #map/place/<id> deep link once the data is loaded
  }

  // Keep the place selection in sync with the URL hash (back/forward + deep links).
  // select()/clearSelection() write the hash; this reads it. The id-equality guard
  // prevents an event loop.
  function reconcilePlace() {
    if (!data) return;
    const id = placeIdFromHash(window.location.hash);
    if (id) {
      if (ui.selected?.id !== id) {
        const f = data.features.find((x) => x.id === id);
        if (f) select(f);
      }
    } else if (ui.selected) {
      clearSelection();
    }
  }

  function onHashChange() {
    syncViewFromHash();
    reconcilePlace();
  }

  async function loadInfo() {
    // Distinguish a network FAILURE (offline/timeout -> retryable) from a panel
    // that is reachable but genuinely missing (a non-OK response -> no error).
    const safe = (url: string): Promise<{ panel: InfoPanel | null; error: boolean }> =>
      dataFetch(url)
        .then(async (r) => {
          if (!r.ok) return { panel: null, error: false }; // reachable but missing
          return { panel: (await r.json()) as InfoPanel, error: false };
        })
        .catch(() => ({ panel: null, error: true })); // offline/timeout -> retryable
    // Derive from DASHBOARDS (single source of truth) so a new dashboard added
    // there is fetched automatically -- never hardcode this list (it silently
    // dropped newly-added panels before).
    const ids = DASHBOARDS.map((d) => d.id);
    // Shared "What this means" summaries for panels whose data-generator doesn't
    // embed one (kept in one committed file so the resident text lives in a single
    // place and survives every tool regeneration).
    type SummaryMap = Record<string, InfoPanel['summary']>;
    const summariesP: Promise<SummaryMap> = dataFetch('summaries.json')
      .then((r) => (r.ok ? (r.json() as Promise<SummaryMap>) : ({} as SummaryMap)))
      .catch(() => ({}) as SummaryMap);
    // Data-freshness dates ("Data as of ...") kept in one committed file for the
    // same reason as summaries: one place to maintain, survives tool regeneration.
    // A panel may also carry its own lastUpdated (from its generator); the overlay
    // only fills in when the panel has none. Non-id keys (e.g. "_note") are ignored.
    type FreshnessMap = Record<string, string>;
    const freshnessP: Promise<FreshnessMap> = dataFetch('freshness.json')
      .then((r) => (r.ok ? (r.json() as Promise<FreshnessMap>) : ({} as FreshnessMap)))
      .catch(() => ({}) as FreshnessMap);
    const [loaded, summaries, freshness] = await Promise.all([
      Promise.all(ids.map((id) => safe(`info-${id}.json`))),
      summariesP,
      freshnessP,
    ]);
    panels = Object.fromEntries(
      ids.map((id, i) => {
        const panel = loaded[i].panel;
        if (panel) {
          if (!panel.summary && summaries[id]) panel.summary = summaries[id];
          if (!panel.lastUpdated && freshness[id]) panel.lastUpdated = freshness[id];
        }
        return [id, panel];
      }),
    );
    panelErrors = Object.fromEntries(ids.map((id, i) => [id, loaded[i].error]));
    infoLoading = false;
  }

  function retryInfo() {
    infoLoading = true;
    loadInfo();
  }

  start().catch((e) => (error = e instanceof Error ? e.message : String(e)));
  loadInfo();

  onMount(() => {
    window.addEventListener('hashchange', onHashChange);
    const stopOnlineWatch = initOnlineWatch();
    return () => {
      window.removeEventListener('hashchange', onHashChange);
      stopOnlineWatch();
    };
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
  // The facet/search-filtered ids, optionally narrowed to saved places (#62) --
  // drives both the map markers and the list.
  const filteredIds = $derived.by(() => {
    const base = new Set(result?.filteredIds ?? []);
    if (!ui.savedOnly) return base;
    return new Set([...base].filter((id) => ui.savedIds.has(id)));
  });

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
  const activePanelError = $derived(isDashboard(ui.view) ? (panelErrors[ui.view] ?? false) : false);
  // The active dashboard's one-line description (menu sub-line); used as a panel
  // subtitle fallback when the panel itself carries none.
  const activeDescription = $derived(
    isDashboard(ui.view) ? DASHBOARDS.find((d) => d.id === ui.view)?.description : undefined,
  );
  // Context header: the dashboard's group label + prev/next for lateral browsing.
  const activeGroup = $derived(isDashboard(ui.view) ? dashboardGroupLabel(ui.view) : null);
  const adjacent = $derived(
    isDashboard(ui.view) ? adjacentDashboards(ui.view) : { prev: null, next: null },
  );
</script>

<div class="app">
  <!-- City alerts ride above the whole shell; renders nothing when none are active. -->
  <AlertBanner />
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
        <!-- Desktop: single Map pill (the map + list already show side by side). -->
        <button class="map-pill" class:active={ui.view === 'map'} onclick={() => setView('map')}>Map</button>
        <!-- Mobile only: segmented Map/List toggle, always available, replaces the Map pill. -->
        <div class="view-toggle" role="group" aria-label="Map or list">
          <button
            class:active={ui.view === 'map' && ui.mobileView === 'map'}
            onclick={() => { setView('map'); setMobileView('map'); }}>Map</button>
          <button
            class:active={ui.view === 'map' && ui.mobileView === 'list'}
            onclick={() => { setView('map'); setMobileView('list'); }}>List</button>
        </div>
        <DashboardMenu />
        <button class:active={ui.view === 'guide'} onclick={() => setView('guide')}>Resident Guide</button>
        <!-- Open Data moved into the dashboards menu (#68); #opendata links still work. -->
      </nav>
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
    <!-- One-tap home row under the header: native app + mobile browsers
         (desktop hides it via its own max-width rule -- map buttons instead). -->
    <QuickActions />
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
        <InfoView
          panel={activePanel}
          loading={infoLoading}
          error={activePanelError}
          onRetry={retryInfo}
          description={activeDescription}
          group={activeGroup}
          prev={adjacent.prev}
          next={adjacent.next}
        />
      </div>
    {:else if ui.view === 'guide'}
      <div class="infowrap">
        <Guide />
      </div>
    {:else if ui.view === 'opendata'}
      <div class="infowrap">
        <OpenData {panels} loading={infoLoading} />
      </div>
    {/if}
  {:else}
    <div class="status">Loading&hellip;</div>
  {/if}

  <InstallPrompt />
  <!-- First-visit orientation modal; shows once, then localStorage keeps it closed. -->
  <WelcomeModal />
  {#if config}
    <!-- "Suggest an edit" / "Add a business" request form (#3); IT-moderated. -->
    <SuggestEdit {config} />
    <!-- "Report an issue" form (#14); private DPW queue, never published. -->
    <ReportIssue {config} />
  {/if}
</div>
