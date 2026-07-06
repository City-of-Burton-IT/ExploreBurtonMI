<script lang="ts">
  import type { AppConfig } from './types';
  import { renderProperties } from './templates';
  import { ui, clearSelection, isSaved, toggleSavedPlace, openSuggest } from './store.svelte';
  import { placeShareUrl } from './hash';
  import Icon from './Icon.svelte';

  const saved = $derived(ui.selected ? isSaved(ui.selected.id) : false);

  let { config }: { config: AppConfig } = $props();

  // Share the current place via a #map/place/<id> permalink: the native share
  // sheet where available (mobile + desktop Chrome), else copy to the clipboard.
  let toast = $state('');
  let toastTimer: ReturnType<typeof setTimeout> | undefined;
  function showToast(msg: string) {
    toast = msg;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast = ''), 2500);
  }
  async function share() {
    const sel = ui.selected;
    if (!sel) return;
    const url = placeShareUrl(sel.id);
    const title = String(sel.properties.name);
    if (navigator.share) {
      try {
        await navigator.share({ title, url });
      } catch {
        /* user cancelled the share sheet -> do nothing */
      }
      return;
    }
    try {
      await navigator.clipboard.writeText(url);
      showToast('Link copied');
    } catch {
      showToast('Copy this link: ' + url);
    }
  }

  const fields = $derived(
    ui.selected ? renderProperties(config.properties, ui.selected.properties) : [],
  );

  // Focus management (mirrors Lightbox.svelte): when the panel opens or switches to
  // a new place, move focus to its heading; when it closes, restore focus to the
  // element that opened it. Escape closes the panel.
  let heading = $state<HTMLHeadingElement>();
  let lastFocus: HTMLElement | null = null;
  let prevId: string | null = null;

  $effect(() => {
    const cur = ui.selected?.id ?? null;
    if (cur && cur !== prevId) {
      lastFocus = (document.activeElement as HTMLElement) ?? null;
      queueMicrotask(() => heading?.focus());
    } else if (!cur && prevId !== null) {
      lastFocus?.focus?.();
      lastFocus = null;
    }
    prevId = cur;
  });

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') clearSelection();
  }
</script>

<svelte:window onkeydown={ui.selected ? onKeydown : undefined} />

{#if ui.selected}
  <aside class="detail" aria-label="Place details">
    <button
      class="save"
      class:saved
      onclick={() => ui.selected && toggleSavedPlace(ui.selected.id)}
      aria-pressed={saved}
      aria-label={saved ? 'Remove from saved places' : 'Save this place'}
      title={saved ? 'Saved, tap to remove' : 'Save this place'}
    >
      <Icon name="star" size={17} fill={saved ? 'currentColor' : 'none'} />
    </button>
    <button class="share" onclick={share} aria-label="Share this place" title="Share this place">
      <Icon name="share-2" size={17} />
    </button>
    <button class="close" onclick={clearSelection} aria-label="Close details">&times;</button>
    <h2 bind:this={heading} tabindex="-1">{ui.selected.properties.name}</h2>
    <dl>
      {#each fields as f (f.label)}
        <dt>{f.label}</dt>
        {#if f.kind === 'link'}
          <dd><a href={f.href} target="_blank" rel="noopener noreferrer">{f.text}</a></dd>
        {:else}
          <dd>{f.value}</dd>
        {/if}
      {/each}
    </dl>
    {#if config.submit?.url}
      <button class="suggest" onclick={() => ui.selected && openSuggest(ui.selected)}>
        Something wrong? Suggest an edit
      </button>
    {/if}
    {#if toast}
      <div class="toast" role="status" aria-live="polite">{toast}</div>
    {/if}
  </aside>
{/if}

<style>
  .detail {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    width: 320px;
    max-width: calc(100% - 1.5rem);
    max-height: calc(100% - 1.5rem);
    overflow-y: auto;
    background: var(--pub-surface);
    border-radius: var(--pub-radius);
    box-shadow: 0 1rem 3rem rgba(0, 0, 0, 0.175);
    padding: 1rem 1.1rem 1.1rem;
    z-index: 1000;
  }

  .close {
    position: absolute;
    top: 0.4rem;
    right: 0.5rem;
    border: none;
    background: none;
    font-size: 1.5rem;
    line-height: 1;
    cursor: pointer;
    color: var(--pub-muted);
  }
  .close:hover {
    color: var(--civic-blue);
  }
  .share {
    position: absolute;
    top: 0.55rem;
    right: 2.3rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    background: none;
    cursor: pointer;
    color: var(--pub-muted);
    padding: 0.1rem;
  }
  .share:hover {
    color: var(--civic-blue);
  }
  .save {
    position: absolute;
    top: 0.55rem;
    right: 4.1rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    background: none;
    cursor: pointer;
    color: var(--pub-muted);
    padding: 0.1rem;
  }
  .save:hover {
    color: var(--civic-blue);
  }
  .save.saved {
    color: var(--civic-blue);
  }
  .share:focus-visible,
  .save:focus-visible,
  .close:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: var(--pub-radius-sm, 8px);
  }
  .suggest {
    margin-top: 0.9rem;
    border: none;
    background: none;
    padding: 0;
    font-family: var(--font-body, sans-serif);
    font-size: 0.82rem;
    color: var(--civic-blue-link);
    text-decoration: underline;
    cursor: pointer;
  }
  .suggest:hover {
    color: var(--civic-blue-deep, #1e437e);
  }
  .suggest:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: var(--pub-radius-sm, 8px);
  }

  .toast {
    margin-top: 0.8rem;
    padding: 0.45rem 0.7rem;
    background: var(--civic-accent-bg);
    color: #fff;
    border-radius: var(--pub-radius-sm, 8px);
    font-size: 0.82rem;
    text-align: center;
  }

  h2 {
    margin: 0 5rem 0.75rem 0;
    font-family: var(--font-head);
    font-weight: 700;
    font-size: 1.15rem;
    color: var(--civic-blue);
  }
  /* The heading is focused programmatically on open (tabindex=-1, not in the Tab
     order), so suppress the UA outline -- no keyboard user lands here via Tab. */
  h2:focus {
    outline: none;
  }

  dl {
    margin: 0;
  }
  dt {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--pub-muted, #5c5c5c);
    margin-top: 0.6rem;
  }
  dd {
    margin: 0.1rem 0 0;
    font-size: 0.95rem;
  }
  a {
    color: var(--civic-blue-link);
  }

  /* Phones/tablets: detail becomes a bottom sheet, not a floating card */
  @media (max-width: 860px) {
    .detail {
      top: auto;
      left: 0;
      right: 0;
      bottom: 0;
      width: 100%;
      max-width: 100%;
      max-height: 65%;
      border-radius: var(--pub-radius-lg) var(--pub-radius-lg) 0 0;
      box-shadow: 0 -0.5rem 2rem rgba(0, 0, 0, 0.2);
      /* The app shell ends above the nav bar (#30), so no safe-area math needed. */
      padding: 1.1rem 1.2rem 1.4rem;
    }
    .close {
      font-size: 1.9rem;
      padding: 0.2rem 0.4rem;
    }
  }
</style>
