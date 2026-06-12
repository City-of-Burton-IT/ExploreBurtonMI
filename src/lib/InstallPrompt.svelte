<script lang="ts">
  import { onMount } from 'svelte';
  import { ui, triggerInstall } from './store.svelte';

  // A dismissible bottom banner. Android/desktop Chromium fire `beforeinstallprompt`
  // (captured in main.ts -> ui.canInstall) so we can show a real "Install" button;
  // iOS Safari has no such API, so we show a manual "Share -> Add to Home Screen"
  // hint instead. Hidden when already installed (standalone) or once dismissed.
  const DISMISS_KEY = 'eb-install-dismissed';

  let isStandalone = $state(false);
  let isIOSSafari = $state(false);
  let dismissed = $state(false);

  onMount(() => {
    const nav = navigator as Navigator & { standalone?: boolean };
    isStandalone =
      window.matchMedia?.('(display-mode: standalone)').matches || nav.standalone === true;
    try {
      dismissed = localStorage.getItem(DISMISS_KEY) === '1';
    } catch {
      /* storage blocked (private mode) -- just show */
    }
    const ua = navigator.userAgent;
    const isIOS =
      /iphone|ipad|ipod/i.test(ua) ||
      (nav.platform === 'MacIntel' && (nav.maxTouchPoints ?? 0) > 1); // iPadOS reports as Mac
    const inSafari = /safari/i.test(ua) && !/crios|fxios|edgios/i.test(ua);
    isIOSSafari = isIOS && inSafari;
  });

  const show = $derived(!isStandalone && !dismissed && (ui.canInstall || isIOSSafari));

  function dismiss() {
    dismissed = true;
    try {
      localStorage.setItem(DISMISS_KEY, '1');
    } catch {
      /* ignore */
    }
  }
  async function install() {
    await triggerInstall();
    dismiss();
  }
</script>

{#if show}
  <div class="install" role="region" aria-label="Install this app">
    <img class="ic" src="/pwa-192.png" alt="" width="36" height="36" />
    <p class="msg">
      {#if ui.canInstall}
        Install <strong>Explore Burton</strong> for one-tap access and offline use.
      {:else}
        Install <strong>Explore Burton</strong>: tap <strong>Share</strong>, then
        <strong>"Add to Home Screen."</strong>
      {/if}
    </p>
    {#if ui.canInstall}
      <button class="go" onclick={install}>Install</button>
    {/if}
    <button class="x" onclick={dismiss} aria-label="Dismiss">&times;</button>
  </div>
{/if}

<style>
  .install {
    position: fixed;
    left: 50%;
    bottom: max(0.9rem, var(--safe-area-inset-bottom, env(safe-area-inset-bottom, 0)));
    transform: translateX(-50%);
    z-index: 2000;
    display: flex;
    align-items: center;
    gap: 0.7rem;
    width: min(92vw, 460px);
    background: var(--pub-surface);
    border: 1px solid var(--pub-border, #e3e3e3);
    border-radius: var(--pub-radius, 12px);
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.22);
    padding: 0.65rem 0.75rem;
  }
  .ic {
    flex: 0 0 auto;
    border-radius: 8px;
  }
  .msg {
    flex: 1 1 auto;
    margin: 0;
    font-size: 0.86rem;
    line-height: 1.35;
    color: var(--pub-ink, #2c2c2c);
  }
  .msg :global(strong) {
    color: var(--civic-blue-deep, #1e437e);
  }
  .go {
    flex: 0 0 auto;
    border: none;
    background: var(--civic-accent-bg);
    color: #fff;
    font-family: var(--font-body);
    font-weight: 700;
    font-size: 0.86rem;
    padding: 0.45rem 0.9rem;
    border-radius: 999px;
    cursor: pointer;
  }
  .go:hover {
    background: var(--civic-accent-bg-hover);
  }
  .go:focus-visible,
  .x:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .x {
    flex: 0 0 auto;
    border: none;
    background: none;
    font-size: 1.4rem;
    line-height: 1;
    color: var(--pub-muted, #5c5c5c);
    cursor: pointer;
    padding: 0 0.2rem;
  }
  .x:hover {
    color: var(--pub-ink, #2c2c2c);
  }
</style>
