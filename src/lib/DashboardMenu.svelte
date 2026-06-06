<script lang="ts">
  import { ui, setView, DASHBOARDS } from './store.svelte';
  import type { InfoView } from './types';

  let open = $state(false);
  let root = $state<HTMLDivElement>();

  const active = $derived(DASHBOARDS.find((d) => d.id === ui.view) ?? null);

  function choose(id: InfoView) {
    setView(id);
    open = false;
  }

  // Close on outside-click or Escape while the menu is open. The listeners are
  // added in an effect (after the opening click has finished), so they never
  // catch the click that opened the menu.
  $effect(() => {
    if (!open) return;
    const onPointer = (e: MouseEvent) => {
      if (root && !root.contains(e.target as Node)) open = false;
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') open = false;
    };
    window.addEventListener('pointerdown', onPointer);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('pointerdown', onPointer);
      window.removeEventListener('keydown', onKey);
    };
  });
</script>

<div class="dash" bind:this={root}>
  <button
    class="trigger"
    class:active={!!active}
    aria-haspopup="menu"
    aria-expanded={open}
    onclick={() => (open = !open)}
  >
    {active ? active.label : 'Dashboards'}
    <span class="caret" class:up={open} aria-hidden="true">▾</span>
  </button>

  {#if open}
    <div class="menu" role="menu" aria-label="Dashboards">
      {#each DASHBOARDS as d (d.id)}
        <button
          role="menuitem"
          class:current={d.id === ui.view}
          onclick={() => choose(d.id)}
        >
          {d.label}
          {#if d.id === ui.view}<span class="check" aria-hidden="true">✓</span>{/if}
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .dash {
    position: relative;
    display: inline-flex;
  }
  .trigger {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border: 1px solid var(--civic-blue);
    background: #fff;
    color: var(--civic-blue);
    font-family: var(--font-body);
    font-weight: 700;
    font-size: 0.85rem;
    padding: 0.4rem 0.9rem;
    border-radius: 999px;
    white-space: nowrap;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }
  .trigger:hover {
    background: var(--civic-blue-soft);
  }
  .trigger.active {
    background: var(--civic-blue);
    color: #fff;
  }
  .trigger:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .caret {
    font-size: 0.7rem;
    transition: transform 0.15s;
  }
  .caret.up {
    transform: rotate(180deg);
  }
  .menu {
    position: absolute;
    top: calc(100% + 6px);
    left: 50%;
    transform: translateX(-50%);
    min-width: 200px;
    background: #fff;
    border: 1px solid var(--pub-border, #d8dde4);
    border-radius: var(--pub-radius, 12px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
    padding: 0.35rem;
    z-index: 1500;
    display: flex;
    flex-direction: column;
  }
  .menu button {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    width: 100%;
    text-align: left;
    border: none;
    background: none;
    border-radius: var(--pub-radius-sm, 8px);
    padding: 0.55rem 0.7rem;
    font-family: var(--font-body);
    font-size: 0.9rem;
    color: var(--pub-ink, #2c2c2c);
    cursor: pointer;
  }
  .menu button:hover {
    background: #f5f7fa;
  }
  .menu button.current {
    color: var(--civic-blue-deep, #1e437e);
    font-weight: 700;
    background: var(--civic-blue-soft, #d7e1f3);
  }
  .menu button:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .check {
    color: var(--civic-blue, #2c57a0);
    font-weight: 700;
  }
</style>
