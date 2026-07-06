<script lang="ts">
  import { onMount } from 'svelte';
  import { dataFetch } from './remote';
  import { persistedStringSet } from './persisted.svelte';
  import { safeHref } from './templates';
  import { activeAlerts, loadAlerts, type CityAlert, type AlertLevel } from './alerts';
  import { localTodayISO } from './closures';
  import Icon from './Icon.svelte';

  // The live banner endpoint (config.alerts.url). Undefined until config loads (this
  // component mounts above the config gate); the loader falls back to the committed
  // alerts.json when it's absent, and the $effect re-runs once it arrives.
  let { alertsUrl }: { alertsUrl?: string } = $props();

  // Icon registry names per alert level (icons.ts).
  const LEVEL_ICON: Record<AlertLevel, string> = {
    emergency: 'alert-emergency',
    warning: 'alert-warning',
    info: 'alert-info',
  };

  let alerts = $state<CityAlert[]>([]);
  const dismissed = persistedStringSet('eb-alerts-dismissed');
  let today = $state('');

  onMount(() => {
    // Local calendar date (not UTC) so "today" matches the resident's clock.
    today = localTodayISO();
  });

  // Load alerts live-first (the read flow), falling back to the committed alerts.json.
  // Re-runs when alertsUrl resolves from config. dataFetch keeps the native hybrid
  // (live site -> bundled) for the alerts.json fallback.
  $effect(() => {
    loadAlerts(alertsUrl, dataFetch).then((a) => {
      alerts = a;
    });
  });

  const shown = $derived(today ? activeAlerts(alerts, today, dismissed.value) : []);
</script>

{#if shown.length}
  <div class="alerts" role="region" aria-label="City alerts">
    {#each shown as a (a.id)}
      <div class="alert level--{a.level}" role={a.level === 'emergency' ? 'alert' : 'status'}>
        <Icon name={LEVEL_ICON[a.level]} size={22} class="icon" />
        <div class="body">
          <p class="text"><strong>{a.title}</strong> {a.message}</p>
          {#if a.link}
            <a class="link" href={safeHref(a.link.href)} target="_blank" rel="noopener noreferrer"
              >{a.link.text}</a
            >
          {/if}
        </div>
        <button class="close" onclick={() => dismissed.add(a.id)} aria-label="Dismiss this alert">
          <Icon name="x" size={18} />
        </button>
      </div>
    {/each}
  </div>
{/if}

<style>
  .alerts {
    display: flex;
    flex-direction: column;
  }
  .alert {
    display: flex;
    align-items: flex-start;
    gap: 0.7rem;
    padding: 0.65rem 1rem;
    color: #fff;
    border-bottom: 1px solid rgba(255, 255, 255, 0.25);
  }
  /* Icon.svelte renders the <svg> in its own component scope; :global() reaches
     through to it (same idiom as Guide.svelte's `.sectionnav button :global(.gicon)`). */
  .alert :global(.icon) {
    flex: 0 0 auto;
    margin-top: 0.05rem;
  }
  .body {
    flex: 1 1 auto;
    min-width: 0;
  }
  .text {
    margin: 0;
    line-height: 1.45;
    font-size: 0.92rem;
  }
  .link {
    display: inline-block;
    margin-top: 0.2rem;
    color: #fff;
    font-weight: 700;
    font-size: 0.88rem;
    text-decoration: underline;
  }
  .close {
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
    border-radius: var(--pub-radius-sm, 8px);
    width: 1.9rem;
    height: 1.9rem;
    cursor: pointer;
  }
  .close:hover {
    background: rgba(255, 255, 255, 0.3);
  }
  .close:focus-visible {
    outline: 2px solid #fff;
    outline-offset: 1px;
  }
  /* Level colours: red / amber / civic blue. Each meets WCAG AA with white text. */
  .level--emergency {
    background: var(--pub-error);
  }
  .level--warning {
    background: var(--pub-warn);
  }
  .level--info {
    background: var(--civic-accent-bg);
  }
</style>
