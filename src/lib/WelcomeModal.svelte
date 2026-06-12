<script lang="ts">
  import { ui, setView, DASHBOARDS, registerOverlay } from './store.svelte';
  import { WELCOME_STORAGE_KEY, welcomeDismissed } from './welcome';

  // First-visit orientation as a one-time modal (not an inline strip): a new
  // resident sees what the site offers, then closes it. Dismissal persists per
  // device. On a native first launch the WebView storage is empty -> this also
  // serves as the app's first-run onboarding (#59), no duplicate component.
  // Focus management mirrors Lightbox.svelte (focus in on open, Escape / backdrop
  // close, restore focus on close).
  let dismissed = $state(true);
  try {
    dismissed = welcomeDismissed(localStorage.getItem(WELCOME_STORAGE_KEY));
  } catch {
    dismissed = false; // storage unavailable -> still show once
  }

  const open = $derived(!dismissed);
  let lastFocus: HTMLElement | null = null;
  let closeBtn = $state<HTMLButtonElement>();

  $effect(() => {
    if (open) {
      lastFocus = (document.activeElement as HTMLElement) ?? null;
      queueMicrotask(() => closeBtn?.focus());
    }
  });

  // While open, let the Android hardware back button dismiss the welcome modal
  // (same as Escape) before it changes the view or exits the app.
  $effect(() => {
    if (open) return registerOverlay(dismiss);
  });

  function dismiss() {
    dismissed = true;
    try {
      localStorage.setItem(WELCOME_STORAGE_KEY, '1');
    } catch {
      /* private mode -> just hide for this session */
    }
    lastFocus?.focus?.();
  }

  const firstDashboard = DASHBOARDS[0]?.id;
  function goDashboards() {
    dismiss();
    if (firstDashboard) setView(firstDashboard);
  }
  function goGuide() {
    dismiss();
    setView('guide');
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') dismiss();
  }
</script>

<svelte:window onkeydown={open ? onKeydown : undefined} />

{#if open}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    class="backdrop"
    role="presentation"
    onclick={(e) => {
      if (e.target === e.currentTarget) dismiss();
    }}
  >
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="welcome-title" tabindex="-1">
      <button bind:this={closeBtn} class="close" onclick={dismiss} aria-label="Close">&times;</button>
      <h2 id="welcome-title">Welcome to Explore Burton</h2>
      <p class="lead">Your interactive guide to the City of Burton. You can:</p>
      <div class="options">
        <button class="opt" onclick={dismiss}>
          <span class="opt-title">Browse the map</span>
          <span class="opt-desc">Find city businesses, government, and services near you.</span>
        </button>
        {#if firstDashboard}
          <button class="opt" onclick={goDashboards}>
            <span class="opt-title">Community dashboards</span>
            <span class="opt-desc">Explore Burton's people, money, health, and infrastructure.</span>
          </button>
        {/if}
        <button class="opt" onclick={goGuide}>
          <span class="opt-title">Resident Guide</span>
          <span class="opt-desc">Trash days, permits, meetings, elections, and more.</span>
        </button>
      </div>
      <button class="primary" onclick={dismiss}>Start exploring</button>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 2500;
    background: rgba(0, 0, 0, 0.5);
    display: grid;
    place-items: center;
    padding: 1.2rem;
  }
  .modal {
    position: relative;
    width: 100%;
    max-width: 460px;
    max-height: calc(100% - 2rem);
    overflow-y: auto;
    background: var(--pub-surface);
    border-radius: var(--pub-radius-lg, 16px);
    box-shadow: 0 1.5rem 4rem rgba(0, 0, 0, 0.3);
    padding: 1.6rem 1.6rem 1.4rem;
  }
  .close {
    position: absolute;
    top: 0.6rem;
    right: 0.7rem;
    border: none;
    background: none;
    font-size: 1.7rem;
    line-height: 1;
    color: var(--pub-muted, #5c5c5c);
    cursor: pointer;
  }
  .close:hover {
    color: var(--civic-blue, #2c57a0);
  }
  .close:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: var(--pub-radius-sm, 8px);
  }
  h2 {
    margin: 0 1.5rem 0.3rem 0;
    font-family: var(--font-head, sans-serif);
    font-weight: 700;
    font-size: 1.4rem;
    color: var(--civic-blue, #2c57a0);
  }
  .lead {
    margin: 0 0 1rem;
    color: var(--pub-ink, #2c2c2c);
  }
  .options {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }
  .opt {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    text-align: left;
    border: 1px solid var(--pub-border, #d8dde4);
    background: var(--pub-surface);
    border-radius: var(--pub-radius, 12px);
    padding: 0.7rem 0.9rem;
    cursor: pointer;
    font-family: var(--font-body, sans-serif);
  }
  .opt:hover {
    border-color: var(--civic-blue, #2c57a0);
    background: var(--civic-blue-soft, #d7e1f3);
  }
  .opt:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .opt-title {
    font-weight: 700;
    color: var(--civic-blue-deep, #1e437e);
  }
  .opt-desc {
    font-size: 0.85rem;
    color: var(--pub-muted, #5c5c5c);
    line-height: 1.35;
  }
  .primary {
    margin-top: 1.1rem;
    width: 100%;
    border: none;
    background: var(--civic-accent-bg);
    color: #fff;
    border-radius: 999px;
    padding: 0.6rem 1rem;
    font-family: var(--font-body, sans-serif);
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
  }
  .primary:hover {
    background: var(--civic-accent-bg-hover);
  }
  .primary:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
</style>
