<script lang="ts">
  import { tick } from 'svelte';
  import { ui, setView, DASHBOARDS, DASHBOARD_GROUPS } from './store.svelte';
  import type { InfoView } from './types';

  let open = $state(false);
  let root = $state<HTMLDivElement>();
  let trigger = $state<HTMLButtonElement>();

  const active = $derived(DASHBOARDS.find((d) => d.id === ui.view) ?? null);

  // A disclosure (not a role=menu): the items are ordinary buttons, so Tab works
  // natively; arrow keys + Home/End are an enhancement, and focus moves into the
  // list on open and returns to the trigger on close/Escape.
  function items(): HTMLButtonElement[] {
    return root ? Array.from(root.querySelectorAll<HTMLButtonElement>('.menu button')) : [];
  }

  async function openMenu() {
    open = true;
    await tick();
    const its = items();
    (its.find((b) => b.dataset.id === ui.view) ?? its[0])?.focus();
  }

  function closeMenu(returnFocus = true) {
    open = false;
    if (returnFocus) trigger?.focus();
  }

  function choose(id: InfoView) {
    setView(id);
    closeMenu();
  }

  function onTriggerKey(e: KeyboardEvent) {
    if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      openMenu();
    }
  }

  function onMenuKey(e: KeyboardEvent) {
    const its = items();
    const i = its.indexOf(document.activeElement as HTMLButtonElement);
    if (e.key === 'Escape') {
      e.preventDefault();
      closeMenu();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      its[(i + 1) % its.length]?.focus();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      its[(i - 1 + its.length) % its.length]?.focus();
    } else if (e.key === 'Home') {
      e.preventDefault();
      its[0]?.focus();
    } else if (e.key === 'End') {
      e.preventDefault();
      its[its.length - 1]?.focus();
    }
  }

  // Close on outside pointer-down (keyboard close is handled in onMenuKey). Added
  // in an effect after the opening interaction, so it never catches that click.
  $effect(() => {
    if (!open) return;
    const onPointer = (e: MouseEvent) => {
      if (root && !root.contains(e.target as Node)) open = false;
    };
    window.addEventListener('pointerdown', onPointer);
    return () => window.removeEventListener('pointerdown', onPointer);
  });
</script>

<div class="dash" bind:this={root}>
  <button
    bind:this={trigger}
    class="trigger"
    class:active={!!active}
    aria-haspopup="true"
    aria-expanded={open}
    onclick={() => (open ? closeMenu(false) : openMenu())}
    onkeydown={onTriggerKey}
  >
    <!-- Desktop/tablet shows the active dashboard's name; phones show a fixed
         "Dashboards" so the trigger width stays bounded and the nav fits one row
         (the active pill styling + the panel title already show which one). -->
    <span class="lbl-active">{active ? active.label : 'Dashboards'}</span>
    <span class="lbl-compact">Dashboards</span>
    <span class="caret" class:up={open} aria-hidden="true">▾</span>
  </button>

  {#if open}
    <div class="menu" role="group" aria-label="Dashboards">
      {#each DASHBOARD_GROUPS as group (group.label)}
        <!-- Each category is a column on desktop (mega-menu) and a stacked block on
             mobile (single-column dropdown). -->
        <div class="col">
          <p class="group-label" aria-hidden="true">{group.label}</p>
          {#each group.items as d (d.id)}
            <button
              data-id={d.id}
              class:current={d.id === ui.view}
              aria-current={d.id === ui.view ? 'true' : undefined}
              onclick={() => choose(d.id)}
              onkeydown={onMenuKey}
            >
              <span class="item-text">
                <span class="item-label">{d.label}</span>
                {#if d.description}<span class="item-desc">{d.description}</span>{/if}
              </span>
              {#if d.id === ui.view}<span class="check" aria-hidden="true">✓</span>{/if}
            </button>
          {/each}
        </div>
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
    background: var(--pub-surface);
    color: var(--civic-blue);
    font-family: var(--font-body);
    font-weight: 700;
    font-size: 0.85rem;
    padding: 0.4rem 0.9rem;
    border-radius: 999px;
    white-space: nowrap;
    cursor: pointer;
    transition: background var(--motion-duration), color var(--motion-duration);
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
  .lbl-compact {
    display: none;
  }
  /* Match the smaller section pills on phones, and show the fixed "Dashboards"
     label (not the longer active-dashboard name) so the nav fits one row. */
  @media (max-width: 860px) {
    .trigger {
      font-size: 0.78rem;
      padding: 0.32rem 0.46rem;
      /* Match the section pills + Map/List toggle (38px outer) so the header
         row is uniform on phones. */
      min-height: 38px;
    }
    .lbl-active {
      display: none;
    }
    .lbl-compact {
      display: inline;
    }
  }
  .caret {
    font-size: 0.7rem;
    transition: transform var(--motion-duration);
  }
  .caret.up {
    transform: rotate(180deg);
  }
  .menu {
    position: absolute;
    top: calc(100% + 6px);
    left: 50%;
    transform: translateX(-50%);
    min-width: 268px;
    max-width: 320px;
    max-height: min(70vh, 520px);
    overflow-y: auto;
    background: var(--pub-surface);
    border: 1px solid var(--pub-border, #e3e3e3);
    border-radius: var(--pub-radius, 12px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
    padding: 0.35rem;
    z-index: 1500;
    display: flex;
    flex-direction: column;
  }
  .col {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .col > .group-label {
    margin-top: 0.2rem;
  }
  /* Desktop: a multi-column "mega menu" so every category is visible at once;
     mobile keeps the single-column dropdown (the default above). */
  @media (min-width: 861px) {
    .menu {
      /* Right-align under the trigger (which sits on the right of the nav) so the
         wide menu extends LEFT and never overflows the viewport right edge. */
      left: auto;
      right: 0;
      transform: none;
      flex-flow: row wrap;
      align-items: flex-start;
      width: min(92vw, 760px);
      max-width: 92vw;
      max-height: min(80vh, 560px);
    }
    .col {
      flex: 1 1 140px;
      min-width: 140px;
      max-width: 180px;
    }
  }
  .menu button {
    display: flex;
    align-items: flex-start;
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
  .item-text {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
  }
  /* Sub-line stays muted + normal weight even when the item is current/bold. */
  .item-desc {
    font-size: 0.72rem;
    font-weight: 400;
    line-height: 1.25;
    color: var(--pub-muted, #6b7280);
  }
  .menu button:hover {
    background: var(--pub-surface-2);
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
  .group-label {
    margin: 0.4rem 0.5rem 0.15rem;
    font-family: var(--font-head, sans-serif);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--pub-muted, #6b7280);
  }
  .group-label:first-child {
    margin-top: 0.2rem;
  }
  /* Sub-dashboards sit slightly indented beneath their category heading. */
  .menu button {
    padding-left: 1rem;
  }
  .check {
    color: var(--civic-blue, #2c57a0);
    font-weight: 700;
  }
</style>
