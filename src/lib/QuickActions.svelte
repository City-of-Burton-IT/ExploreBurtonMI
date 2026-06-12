<script lang="ts">
  import { Capacitor } from '@capacitor/core';
  import { ui, setGuideSection, requestNearMe, openReport } from './store.svelte';
  import { QUICK_ACTION_GUIDE_SECTIONS as TARGET } from './quickActions';

  // A compact home row of one-tap actions, shown ONLY in the native app on the
  // map view (a single conditional component -- no fork; the web build never
  // renders it). Each action routes into an existing view/widget, so a fresh
  // launch reaches the waste lookup, meetings, or contacts in one tap.
  const show = Capacitor.isNativePlatform();

  // Lucide (https://lucide.dev, ISC) inner SVG markup -- inline, no icon dep
  // (same approach as AlertBanner / GuideIcon / OfflineBadge).
  const ICONS = {
    near: '<circle cx="12" cy="12" r="10"/><line x1="22" x2="18" y1="12" y2="12"/><line x1="6" x2="2" y1="12" y2="12"/><line x1="12" x2="12" y1="6" y2="2"/><line x1="12" x2="12" y1="22" y2="18"/>',
    waste:
      '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>',
    meetings:
      '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
    contact:
      '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
    report:
      '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 20h16a2 2 0 0 0 1.73-2Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  };

  // Guide section ids are the single source of truth in content/guide/index.json.
  const actions: { label: string; icon: string; run: () => void }[] = [
    { label: 'Near me', icon: ICONS.near, run: requestNearMe },
    { label: 'Waste pickup', icon: ICONS.waste, run: () => setGuideSection(TARGET.waste) },
    { label: 'Meetings', icon: ICONS.meetings, run: () => setGuideSection(TARGET.meetings) },
    { label: 'Contact', icon: ICONS.contact, run: () => setGuideSection(TARGET.contact) },
    // One-tap path into the #14 issue-report form (pothole/blight/sign/...).
    { label: 'Report', icon: ICONS.report, run: openReport },
  ];
</script>

{#if show && ui.view === 'map'}
  <nav class="quick-actions" aria-label="Quick actions">
    {#each actions as a (a.label)}
      <button type="button" onclick={a.run}>
        <svg
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true">{@html a.icon}</svg
        >
        <span>{a.label}</span>
      </button>
    {/each}
  </nav>
{/if}

<style>
  .quick-actions {
    display: flex;
    gap: 0.4rem;
    padding: 0.5rem 0.6rem;
    background: var(--pub-surface);
    border-bottom: 1px solid var(--pub-border, #e3e3e3);
    overflow-x: auto;
  }
  button {
    flex: 1 1 0;
    min-width: 4.2rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.2rem;
    padding: 0.5rem 0.3rem;
    border: 1px solid var(--pub-border, #d8dde4);
    border-radius: var(--pub-radius, 12px);
    background: var(--civic-blue-soft, #d7e1f3);
    color: var(--civic-blue-deep, #1e437e);
    font-family: var(--font-body, sans-serif);
    font-size: 0.74rem;
    font-weight: 700;
    line-height: 1.1;
    cursor: pointer;
  }
  button:active {
    background: var(--civic-accent-bg);
    color: #fff;
  }
  button:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  span {
    text-align: center;
  }
</style>
