<script lang="ts">
  import { setView } from './store.svelte';
  import type { DashboardItem } from './store.svelte';

  // Previous/next dashboard footer navigation. Renders nothing when the panel
  // isn't part of a browsable sequence.
  let { prev, next }: { prev?: DashboardItem | null; next?: DashboardItem | null } = $props();
</script>

{#if prev || next}
  <nav class="dashnav" aria-label="Browse dashboards">
    {#if prev}
      <button class="nav-btn prev" type="button" onclick={() => setView(prev.id)}>
        <span class="dir" aria-hidden="true">‹</span>
        <span class="lbl"><span class="cue">Previous</span>{prev.label}</span>
      </button>
    {:else}<span></span>{/if}
    {#if next}
      <button class="nav-btn next" type="button" onclick={() => setView(next.id)}>
        <span class="lbl"><span class="cue">Next</span>{next.label}</span>
        <span class="dir" aria-hidden="true">›</span>
      </button>
    {/if}
  </nav>
{/if}

<style>
  .dashnav {
    display: flex;
    justify-content: space-between;
    gap: 0.6rem;
    margin-top: 1.2rem;
  }
  .nav-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    max-width: 48%;
    border: 1px solid var(--pub-border, #d8dde4);
    background: var(--pub-surface);
    border-radius: var(--pub-radius, 10px);
    padding: 0.5rem 0.8rem;
    cursor: pointer;
    font-family: var(--font-body, sans-serif);
    color: var(--civic-blue-deep, #1e437e);
    text-align: left;
  }
  .nav-btn.next {
    text-align: right;
  }
  .nav-btn:hover {
    border-color: var(--civic-blue, #2c57a0);
    background: var(--civic-blue-soft, #d7e1f3);
  }
  .nav-btn:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .nav-btn .lbl {
    display: flex;
    flex-direction: column;
    min-width: 0;
    font-weight: 700;
    font-size: 0.86rem;
  }
  .nav-btn .cue {
    font-size: 0.66rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--pub-muted, #6b7280);
  }
  .nav-btn .dir {
    font-size: 1.2rem;
    line-height: 1;
    flex: 0 0 auto;
  }
</style>
