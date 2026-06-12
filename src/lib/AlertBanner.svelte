<script lang="ts">
  import { onMount } from 'svelte';
  import { dataFetch } from './remote';
  import { safeHref } from './templates';
  import { activeAlerts, type AlertsBundle, type CityAlert, type AlertLevel } from './alerts';

  // Lucide (https://lucide.dev, ISC/MIT) inner SVG markup, rendered in a 24x24
  // currentColor stroke icon (same approach as the Resident Guide's GuideIcon).
  const LEVEL_ICON: Record<AlertLevel, string> = {
    emergency:
      '<path d="M12 16h.01"/><path d="M12 8v4"/><path d="M15.312 2a2 2 0 0 1 1.414.586l4.688 4.688A2 2 0 0 1 22 8.688v6.624a2 2 0 0 1-.586 1.414l-4.688 4.688a2 2 0 0 1-1.414.586H8.688a2 2 0 0 1-1.414-.586l-4.688-4.688A2 2 0 0 1 2 15.312V8.688a2 2 0 0 1 .586-1.414l4.688-4.688A2 2 0 0 1 8.688 2z"/>',
    warning:
      '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
  };

  const STORAGE_KEY = 'eb-alerts-dismissed';
  const pad = (n: number): string => String(n).padStart(2, '0');

  let alerts = $state<CityAlert[]>([]);
  let dismissed = $state<Set<string>>(new Set());
  let today = $state('');

  function loadDismissed(): Set<string> {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return new Set(raw ? (JSON.parse(raw) as string[]) : []);
    } catch {
      return new Set();
    }
  }

  function persist(ids: Set<string>): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids]));
    } catch {
      /* private mode / storage disabled -> dismissal just doesn't persist */
    }
  }

  onMount(async () => {
    dismissed = loadDismissed();
    const d = new Date();
    // Local calendar date (not UTC) so "today" matches the resident's clock.
    today = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    try {
      const r = await dataFetch('alerts.json');
      if (r.ok) {
        const b = (await r.json()) as AlertsBundle;
        alerts = b.alerts ?? [];
      }
    } catch {
      alerts = [];
    }
  });

  const shown = $derived(today ? activeAlerts(alerts, today, dismissed) : []);

  function dismiss(id: string): void {
    const next = new Set(dismissed);
    next.add(id);
    dismissed = next; // reassign so Svelte re-derives `shown`
    persist(next);
  }
</script>

{#if shown.length}
  <div class="alerts" role="region" aria-label="City alerts">
    {#each shown as a (a.id)}
      <div class="alert level--{a.level}" role={a.level === 'emergency' ? 'alert' : 'status'}>
        <svg
          class="icon"
          viewBox="0 0 24 24"
          width="22"
          height="22"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true">{@html LEVEL_ICON[a.level]}</svg
        >
        <div class="body">
          <p class="text"><strong>{a.title}</strong> {a.message}</p>
          {#if a.link}
            <a class="link" href={safeHref(a.link.href)} target="_blank" rel="noopener noreferrer"
              >{a.link.text}</a
            >
          {/if}
        </div>
        <button class="close" onclick={() => dismiss(a.id)} aria-label="Dismiss this alert">
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg
          >
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
  .icon {
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
