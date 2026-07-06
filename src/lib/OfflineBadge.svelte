<script lang="ts">
  import { ui } from './store.svelte';
  import Icon from './Icon.svelte';

  // Signposts that the device is offline so cached/stale content reads as
  // "saved" rather than current. Shown on the Resident Guide and the live
  // widgets (meetings, waste lookup). Applies on web + native alike -- offline
  // is offline. `ui.online` is kept current by initOnlineWatch() (App onMount).
  let { label = 'Offline: showing saved info' }: { label?: string } = $props();
</script>

{#if !ui.online}
  <p class="offline-badge" role="status">
    <Icon name="wifi-off" size={16} class="icon" />
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
  /* Icon.svelte renders the <svg> in its own component scope; :global() reaches
     through to it (same idiom as Guide.svelte's `.sectionnav button :global(.gicon)`). */
  .offline-badge :global(.icon) {
    flex: none;
  }
</style>
