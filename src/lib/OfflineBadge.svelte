<script lang="ts">
  import { ui } from './store.svelte';

  // Signposts that the device is offline so cached/stale content reads as
  // "saved" rather than current. Shown on the Resident Guide and the live
  // widgets (meetings, waste lookup). Applies on web + native alike -- offline
  // is offline. `ui.online` is kept current by initOnlineWatch() (App onMount).
  let { label = 'Offline -- showing saved info' }: { label?: string } = $props();

  // Lucide wifi-off (https://lucide.dev, ISC), inner SVG markup -- same inline
  // approach as AlertBanner / GuideIcon (no icon dependency).
  const WIFI_OFF =
    '<path d="M12 20h.01"/><path d="M8.5 16.429a5 5 0 0 1 7 0"/><path d="M5 12.859a10 10 0 0 1 5.17-2.69"/><path d="M19 12.859a10 10 0 0 0-2.007-1.523"/><path d="M2 8.82a15 15 0 0 1 4.177-2.643"/><path d="M22 8.82a15 15 0 0 0-11.288-3.764"/><path d="m2 2 20 20"/>';
</script>

{#if !ui.online}
  <p class="offline-badge" role="status">
    <svg
      class="icon"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true">{@html WIFI_OFF}</svg
    >
    <span>{label}</span>
  </p>
{/if}

<style>
  .offline-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0 0 0.8rem;
    padding: 0.35rem 0.7rem;
    border: 1px solid var(--pub-border, #d8dde4);
    border-radius: 999px;
    background: var(--pub-surface-muted, #f3f4f6);
    color: var(--pub-muted, #5c5c5c);
    font-size: 0.82rem;
    font-weight: 600;
    line-height: 1.2;
  }
  .icon {
    flex: none;
  }
</style>
