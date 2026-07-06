<script lang="ts">
  import { Capacitor } from '@capacitor/core';
  import { ui, setGuideSection, requestNearMe, openReport, openSettings } from './store.svelte';
  import { QUICK_ACTION_GUIDE_SECTIONS as TARGET } from './quickActions';
  import Icon from './Icon.svelte';

  // A compact home row of one-tap actions on the map view, for PHONES: the
  // native app and mobile browsers alike (#68 follow-up -- the Near-me/Report
  // map buttons are desktop-only now, so this row is the phone path to those
  // actions). Native always shows it; on the web a max-width rule hides it on
  // desktop, where the map buttons exist instead.
  const native = Capacitor.isNativePlatform();

  // Icon names resolve against the shared registry (icons.ts); "meetings" is
  // the same Lucide markup the Resident Guide uses for its Meetings section,
  // so it's shared rather than duplicated here.
  const ICONS = {
    near: 'locate',
    bell: 'bell-notify',
    waste: 'trash-2',
    meetings: 'meetings',
    contact: 'phone',
    report: 'triangle-alert',
  };

  // Guide section ids are the single source of truth in content/guide/index.json.
  // The row differs by platform: push works only in the app, so "Notifications"
  // is native-only; the web instead keeps "Waste pickup" (and Settings is still
  // reachable via the menu-bar cog). The app drops "Meetings" to keep the row short.
  type Action = { label: string; icon: string; run: () => void };
  const nearMe: Action = { label: 'Near me', icon: ICONS.near, run: requestNearMe };
  const contact: Action = { label: 'Contact', icon: ICONS.contact, run: () => setGuideSection(TARGET.contact) };
  const report: Action = { label: 'Report', icon: ICONS.report, run: openReport };

  const actions: Action[] = native
    ? [
        nearMe,
        { label: 'Notifications', icon: ICONS.bell, run: openSettings },
        contact,
        report,
      ]
    : [
        nearMe,
        { label: 'Waste pickup', icon: ICONS.waste, run: () => setGuideSection(TARGET.waste) },
        { label: 'Meetings', icon: ICONS.meetings, run: () => setGuideSection(TARGET.meetings) },
        contact,
        report,
      ];
</script>

{#if ui.view === 'map'}
  <nav class="quick-actions" class:web={!native} aria-label="Quick actions">
    {#each actions as a (a.label)}
      <button type="button" onclick={a.run}>
        <Icon name={a.icon} size={22} />
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
  /* On the web this row is the PHONE path to Near me / Report (#68 follow-up);
     desktop keeps the labeled map buttons instead. Native always shows it. */
  @media (min-width: 861px) {
    .quick-actions.web {
      display: none;
    }
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
