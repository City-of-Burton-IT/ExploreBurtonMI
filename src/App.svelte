<script lang="ts">
  import { onMount, untrack } from 'svelte';
  import { loadConfig } from './lib/config';
  import { loadData } from './lib/data';
  import { filterFeatures } from './lib/filter';
  import { buildIndex, searchIds } from './lib/search';
  import type { AppConfig, PlaceCollection } from './lib/types';
  import { ui, setMobileView, setView, syncViewFromHash, openAbout, openSettings, isDashboard, DASHBOARDS, select, clearSelection, dashboardGroupLabel, adjacentDashboards, initOnlineWatch } from './lib/store.svelte';
  import { placeIdFromHash } from './lib/hash';
  import { haversineMeters } from './lib/reverseGeocode';
  import Map from './lib/Map.svelte';
  import Detail from './lib/Detail.svelte';
  import Facets from './lib/Facets.svelte';
  import List from './lib/List.svelte';
  import Search from './lib/Search.svelte';
  import About from './lib/About.svelte';
  import Settings from './lib/Settings.svelte';
  import InfoView from './lib/InfoView.svelte';
  import Guide from './lib/Guide.svelte';
  import OpenData from './lib/OpenData.svelte';
  import StatusPage from './lib/StatusPage.svelte';
  import DashboardMenu from './lib/DashboardMenu.svelte';
  import InstallPrompt from './lib/InstallPrompt.svelte';
  import AlertBanner from './lib/AlertBanner.svelte';
  import PushBanner from './lib/PushBanner.svelte';
  import WelcomeModal from './lib/WelcomeModal.svelte';
  import SuggestEdit from './lib/SuggestEdit.svelte';
  import ReportIssue from './lib/ReportIssue.svelte';
  import QuickActions from './lib/QuickActions.svelte';
  import Icon from './lib/Icon.svelte';
  import { createDashboardData } from './lib/dashboard/dashboardData.svelte';

  let config = $state<AppConfig | null>(null);
  let data = $state<PlaceCollection | null>(null);
  let error = $state<string | null>(null);

  const dashboardData = createDashboardData(DASHBOARDS.map(({ id }) => id));

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

  function retryInfo() {
    if (isDashboard(ui.view)) void dashboardData.retry(ui.view);
  }

  start().catch((e) => (error = e instanceof Error ? e.message : String(e)));

  // Route changes are the only trigger for dashboard network work. Keeping the
  // service reads untracked prevents its loading-state updates from retriggering
  // this effect; each route transition issues at most one explicit load request.
  $effect(() => {
    const view = ui.view;
    untrack(() => {
      if (isDashboard(view)) void dashboardData.load(view);
      else if (view === 'opendata') void dashboardData.loadAll();
    });
  });

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

  const filteredFeatures = $derived.by(() => {
    if (!data) return [];
    const feats = data.features.filter((f) => filteredIds.has(f.id));
    const loc = ui.userLocation;
    if (!loc) return feats;
    // Nearest-first once the user shares their location.
    return [...feats].sort((a, b) => {
      const [aLng, aLat] = a.geometry.coordinates;
      const [bLng, bLat] = b.geometry.coordinates;
      return haversineMeters(loc.lat, loc.lng, aLat, aLng) - haversineMeters(loc.lat, loc.lng, bLat, bLng);
    });
  });

  const activeDashboardState = $derived(
    isDashboard(ui.view) ? dashboardData.state(ui.view) : null,
  );
  const activePanel = $derived(activeDashboardState?.panel ?? null);
  const activePanelLoading = $derived(
    !!activeDashboardState && (!activeDashboardState.requested || activeDashboardState.loading),
  );
  const activePanelError = $derived(
    !!activeDashboardState?.error && activeDashboardState.error.kind !== 'missing',
  );
  const openDataLoading = $derived(
    ui.view === 'opendata' && (dashboardData.allLoading || !dashboardData.allLoaded),
  );
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
  <!-- City alerts ride above the whole shell; renders nothing when none are active.
       Reads live from the banner endpoint (config.alerts.url) with alerts.json fallback. -->
  <AlertBanner alertsUrl={config?.alerts?.url} />
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
        <!-- Settings cog: appearance + notifications (#64/#61). Icon-only, far right. -->
        <button
          class="cog"
          class:active={ui.settingsOpen}
          onclick={openSettings}
          aria-label="Settings"
          title="Settings"
        >
          <Icon name="settings" size={18} />
        </button>
      </nav>
      <!-- Trigger lives at the end of the Guide; this keeps the dialog mounted so
           the map © button (and the Guide's About button) can open it. -->
      <About {config} showButton={false} />
      <Settings />
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
          loading={activePanelLoading}
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
        <OpenData panels={dashboardData.panels} loading={openDataLoading} />
      </div>
    {:else if ui.view === 'status'}
      <div class="infowrap">
        <StatusPage statusUrl={config.status?.url ?? ''} />
      </div>
    {/if}
  {:else}
    <div class="status">Loading&hellip;</div>
  {/if}

  <InstallPrompt />
  <!-- Foreground push popup (#64): shows when an FCM message arrives while open. -->
  <PushBanner />
  <!-- First-visit orientation modal; shows once, then localStorage keeps it closed. -->
  <WelcomeModal />
  {#if config}
    <!-- "Suggest an edit" / "Add a business" request form (#3); IT-moderated. -->
    <SuggestEdit {config} />
    <!-- "Report an issue" form (#14); private DPW queue, never published. -->
    <ReportIssue {config} />
  {/if}
</div>
