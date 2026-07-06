<script lang="ts">
  import { ui, dismissPushBanner } from './store.svelte';
  import { applyRoute } from './deepLinks';
  import Icon from './Icon.svelte';

  // Foreground push popup (#64): Android does not raise a tray notification while
  // the app is open, so when an FCM message arrives in-foreground push.ts calls
  // showPushBanner() and this toast appears. Tapping it follows the message's deep
  // link (if any); it also auto-dismisses after a few seconds.

  let timer: ReturnType<typeof setTimeout> | undefined;

  $effect(() => {
    if (ui.pushBanner) {
      clearTimeout(timer);
      timer = setTimeout(() => dismissPushBanner(), 8000);
      return () => clearTimeout(timer);
    }
  });

  function open(): void {
    const url = ui.pushBanner?.url ?? null;
    dismissPushBanner();
    if (url) applyRoute(url);
  }
</script>

{#if ui.pushBanner}
  <div class="push-toast" role="status" aria-live="polite">
    <button class="body" onclick={open}>
      <Icon name="bell-push" size={20} class="bell" />
      <span class="text">
        <span class="title">{ui.pushBanner.title}</span>
        {#if ui.pushBanner.body}<span class="msg">{ui.pushBanner.body}</span>{/if}
      </span>
    </button>
    <button class="close" onclick={dismissPushBanner} aria-label="Dismiss">&times;</button>
  </div>
{/if}

<style>
  .push-toast {
    position: fixed;
    left: 50%;
    transform: translateX(-50%);
    top: calc(env(safe-area-inset-top, 0px) + 0.6rem);
    top: calc(var(--safe-area-inset-top, env(safe-area-inset-top, 0px)) + 0.6rem);
    z-index: 2500;
    width: min(560px, calc(100% - 1.2rem));
    display: flex;
    align-items: stretch;
    gap: 0.25rem;
    background: var(--civic-blue);
    color: #fff;
    border-radius: var(--pub-radius-lg, 12px);
    box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.3);
    overflow: hidden;
  }
  .body {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    border: none;
    background: none;
    color: inherit;
    font-family: var(--font-body);
    text-align: left;
    padding: 0.7rem 0.6rem 0.7rem 0.9rem;
    cursor: pointer;
  }
  /* Icon.svelte renders the <svg> in its own component scope; :global() reaches
     through to it (same idiom as Guide.svelte's `.sectionnav button :global(.gicon)`). */
  .body :global(.bell) {
    flex: none;
  }
  .text {
    display: flex;
    flex-direction: column;
    gap: 0.05rem;
    min-width: 0;
  }
  .title {
    font-weight: 700;
    font-size: 0.9rem;
  }
  .msg {
    font-size: 0.82rem;
    opacity: 0.92;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
  }
  .close {
    flex: none;
    border: none;
    background: none;
    color: #fff;
    font-size: 1.5rem;
    line-height: 1;
    padding: 0 0.8rem;
    cursor: pointer;
    opacity: 0.85;
  }
  .close:hover {
    opacity: 1;
  }
  .body:focus-visible,
  .close:focus-visible {
    outline: none;
    box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.8);
    border-radius: 8px;
  }
</style>
