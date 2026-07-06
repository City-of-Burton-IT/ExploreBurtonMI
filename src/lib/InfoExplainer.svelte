<script lang="ts">
  import type { Snippet } from 'svelte';

  // A collapsible "learn more" disclosure (glossary, methodology): an accent
  // toggle button revealing the caller's content. Starts closed; each instance
  // tracks its own open state.
  let { title, children }: { title: string; children: Snippet } = $props();

  let open = $state(false);
</script>

<div class="explainer">
  <button class="explainer-toggle" aria-expanded={open} onclick={() => (open = !open)}>
    <span class="ex-icon" aria-hidden="true">{open ? '−' : '+'}</span>
    {title}
  </button>
  {#if open}
    <div class="explainer-body">
      {@render children()}
    </div>
  {/if}
</div>

<style>
  .explainer {
    margin-top: 1.8rem;
  }
  .explainer-toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--civic-accent-bg);
    color: #fff;
    border: none;
    border-radius: var(--pub-radius-sm, 6px);
    padding: 0.6rem 1rem;
    font-family: var(--font-head, sans-serif);
    font-weight: 600;
    font-size: 0.95rem;
    cursor: pointer;
  }
  .explainer-toggle:hover {
    background: var(--civic-blue-link, #1a4b8f);
  }
  .ex-icon {
    font-size: 1.1rem;
    line-height: 1;
    font-weight: 700;
  }
  .explainer-body {
    margin-top: 0.8rem;
    animation: ex-reveal 0.22s ease;
  }
  @keyframes ex-reveal {
    from { opacity: 0; transform: translateY(-4px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
