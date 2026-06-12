<script lang="ts">
  import { registerOverlay } from './store.svelte';

  // Reusable image lightbox. Call `show(src, caption)` via a bound instance.
  let open = $state(false);
  let src = $state('');
  let caption = $state('');
  let lastFocus: HTMLElement | null = null;
  let closeBtn = $state<HTMLButtonElement>();

  export function show(imgSrc: string, cap = '') {
    lastFocus = (document.activeElement as HTMLElement) ?? null;
    src = imgSrc;
    caption = cap;
    open = true;
    queueMicrotask(() => closeBtn?.focus());
  }

  function close() {
    open = false;
    lastFocus?.focus?.();
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
  }

  // While open, let the Android hardware back button close the lightbox first.
  $effect(() => {
    if (open) return registerOverlay(close);
  });
</script>

<svelte:window onkeydown={open ? onKeydown : undefined} />

{#if open}
  <!-- Backdrop closes on a click that lands on the backdrop itself (not the image).
       Keyboard close is Esc, handled on window above. -->
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    class="lb-backdrop"
    role="presentation"
    onclick={(e) => {
      if (e.target === e.currentTarget) close();
    }}
  >
    <div class="lb-dialog" role="dialog" aria-modal="true" aria-label={caption || 'Image viewer'} tabindex="-1">
      <button bind:this={closeBtn} class="lb-close" onclick={close} aria-label="Close image">&times;</button>
      <img class="lb-img" {src} alt={caption} />
      {#if caption}<p class="lb-caption">{caption}</p>{/if}
    </div>
  </div>
{/if}

<style>
  .lb-backdrop {
    position: fixed;
    inset: 0;
    z-index: 3000;
    background: rgba(0, 0, 0, 0.82);
    display: grid;
    place-items: center;
    padding: 1.2rem;
  }
  .lb-dialog {
    position: relative;
    max-width: 96vw;
    max-height: 92vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }
  .lb-img {
    max-width: 96vw;
    max-height: 82vh;
    width: auto;
    height: auto;
    border-radius: var(--pub-radius-sm, 8px);
    box-shadow: 0 1rem 3rem rgba(0, 0, 0, 0.5);
  }
  .lb-caption {
    margin: 0;
    color: #fff;
    font-size: 0.88rem;
    text-align: center;
    max-width: 60ch;
  }
  .lb-close {
    position: absolute;
    top: -2.6rem;
    right: 0;
    border: none;
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
    width: 2.1rem;
    height: 2.1rem;
    border-radius: 999px;
    font-size: 1.5rem;
    line-height: 1;
    cursor: pointer;
  }
  .lb-close:hover {
    background: rgba(255, 255, 255, 0.3);
  }
  .lb-close:focus-visible {
    outline: 2px solid #fff;
    outline-offset: 2px;
  }
</style>
