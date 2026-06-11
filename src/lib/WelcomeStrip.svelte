<script lang="ts">
  import { ui, setView, DASHBOARDS } from './store.svelte';

  // First-visit orientation: a dismissible strip above the map that points a new
  // resident at the three things the site offers. Dismissal persists per device.
  const STORAGE_KEY = 'eb-welcome-dismissed';

  let dismissed = $state(true);
  try {
    dismissed = localStorage.getItem(STORAGE_KEY) === '1';
  } catch {
    dismissed = false; // storage unavailable -> still show the strip once
  }

  const show = $derived(ui.view === 'map' && !dismissed);
  const firstDashboard = DASHBOARDS[0]?.id;

  function dismiss() {
    dismissed = true;
    try {
      localStorage.setItem(STORAGE_KEY, '1');
    } catch {
      /* private mode -> just hide for this session */
    }
  }

  function goDashboards() {
    dismiss();
    if (firstDashboard) setView(firstDashboard);
  }
  function goGuide() {
    dismiss();
    setView('guide');
  }
</script>

{#if show}
  <div class="welcome" role="region" aria-label="Welcome to Explore Burton">
    <p class="msg">
      <strong>Welcome to Explore Burton.</strong> Search the map of city businesses and services,
      browse community dashboards, or read the Resident Guide.
    </p>
    <div class="actions">
      <button onclick={dismiss}>Browse the map</button>
      {#if firstDashboard}
        <button onclick={goDashboards}>See city dashboards</button>
      {/if}
      <button onclick={goGuide}>Resident Guide</button>
    </div>
    <button class="close" onclick={dismiss} aria-label="Dismiss welcome">&times;</button>
  </div>
{/if}

<style>
  .welcome {
    position: relative;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 1rem;
    padding: 0.55rem 2.2rem 0.55rem 0.9rem;
    background: var(--civic-blue-soft, #d7e1f3);
    border-bottom: 1px solid var(--pub-border, #e3e3e3);
  }
  .msg {
    margin: 0;
    flex: 1 1 18rem;
    min-width: 0;
    font-size: 0.9rem;
    line-height: 1.4;
    color: var(--civic-blue-deep, #1e437e);
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .actions button {
    border: 1px solid var(--civic-blue, #2c57a0);
    background: #fff;
    color: var(--civic-blue-deep, #1e437e);
    border-radius: 999px;
    padding: 0.3rem 0.8rem;
    font-family: var(--font-body, sans-serif);
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
  }
  .actions button:hover {
    background: var(--civic-blue, #2c57a0);
    color: #fff;
  }
  .actions button:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .close {
    position: absolute;
    top: 0.35rem;
    right: 0.5rem;
    border: none;
    background: none;
    font-size: 1.4rem;
    line-height: 1;
    color: var(--civic-blue-deep, #1e437e);
    cursor: pointer;
  }
  .close:hover {
    color: var(--civic-blue, #2c57a0);
  }
  .close:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: var(--pub-radius-sm, 8px);
  }
</style>
