<script lang="ts">
  import { setView, DASHBOARDS } from './store.svelte';
  import { WELCOME_STORAGE_KEY, welcomeDismissed } from './welcome';
  import Modal from './Modal.svelte';

  // First-visit orientation as a one-time modal (not an inline strip): a new
  // resident sees what the site offers, then closes it. Dismissal persists per
  // device. On a native first launch the WebView storage is empty -> this also
  // serves as the app's first-run onboarding (#59), no duplicate component.
  // Modal mechanics (focus in/out, Escape/backdrop close, Android back) live in
  // the shared <Modal>.
  let dismissed = $state(true);
  try {
    dismissed = welcomeDismissed(localStorage.getItem(WELCOME_STORAGE_KEY));
  } catch {
    dismissed = false; // storage unavailable -> still show once
  }

  const open = $derived(!dismissed);

  function dismiss() {
    dismissed = true;
    try {
      localStorage.setItem(WELCOME_STORAGE_KEY, '1');
    } catch {
      /* private mode -> just hide for this session */
    }
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
</script>

{#if open}
  <Modal
    close={dismiss}
    labelledby="welcome-title"
    style="--modal-max-width: 460px; --modal-z: 2500; --modal-backdrop-bg: rgba(0, 0, 0, 0.5); --modal-shadow: 0 1.5rem 4rem rgba(0, 0, 0, 0.3); --modal-padding: 1.6rem 1.6rem 1.4rem"
  >
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
  </Modal>
{/if}

<style>
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
