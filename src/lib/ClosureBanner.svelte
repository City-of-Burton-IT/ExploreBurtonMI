<script lang="ts">
  import { MDOT_MIDRIVE_URL, closuresSignature, type RoadClosure } from './closures';
  import { persistedString } from './persisted.svelte';

  // Dismissible map callout for active road closures (#32). Dismissal is keyed
  // to the signature of the ACTIVE set, so a new/changed closure brings the
  // banner back even after an earlier dismiss.

  let { active }: { active: RoadClosure[] } = $props();

  const signature = $derived(closuresSignature(active));
  const dismissedSig = persistedString('eb-closures-dismissed');

  const show = $derived(active.length > 0 && signature !== dismissedSig.value);

  function dismiss() {
    dismissedSig.set(signature);
  }

  const roadList = $derived(
    [...new Set(active.map((c) => c.road))].slice(0, 3).join(', ') +
      (new Set(active.map((c) => c.road)).size > 3 ? '...' : ''),
  );
</script>

{#if show}
  <div class="closure-banner" role="status">
    <span class="msg">
      <strong>{active.length} road closure{active.length === 1 ? '' : 's'} in Burton:</strong>
      {roadList}
    </span>
    <a href={MDOT_MIDRIVE_URL} target="_blank" rel="noopener noreferrer">
      State highways: MDOT MiDrive
    </a>
    <button onclick={dismiss} aria-label="Dismiss closure notice">&times;</button>
  </div>
{/if}

<style>
  .closure-banner {
    position: absolute;
    top: 0.75rem;
    left: 50%;
    transform: translateX(-50%);
    z-index: 1100;
    display: flex;
    align-items: center;
    gap: 0.7rem;
    max-width: min(92%, 560px);
    background: var(--pub-warn);
    color: #fff;
    font-size: 0.84rem;
    line-height: 1.3;
    padding: 0.45rem 0.5rem 0.45rem 0.9rem;
    border-radius: var(--pub-radius, 12px);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
  }
  .msg {
    min-width: 0;
  }
  a {
    color: #fff;
    white-space: nowrap;
  }
  button {
    flex: none;
    border: none;
    background: none;
    color: #fff;
    font-size: 1.3rem;
    line-height: 1;
    cursor: pointer;
    padding: 0.1rem 0.3rem;
  }
  button:focus-visible,
  a:focus-visible {
    outline: none;
    box-shadow: 0 0 0 0.18rem rgba(255, 255, 255, 0.6);
    border-radius: 6px;
  }
  @media (max-width: 860px) {
    .closure-banner {
      flex-wrap: wrap;
      top: 0.5rem;
    }
  }
</style>
