<script lang="ts">
  import type { AppConfig, PlaceFeature } from './types';
  import { ui, select, toggleSavedPlace, setSavedOnly, openSuggest } from './store.svelte';
  import Icon from './Icon.svelte';

  let { config, features }: { config: AppConfig; features: PlaceFeature[] } = $props();

  const titleField = $derived(config.list[0]);
  const restFields = $derived(config.list.slice(1));

  function fieldText(feature: PlaceFeature, field: string): string {
    const v = feature.properties[field];
    return v == null ? '' : Array.isArray(v) ? v.join(', ') : String(v);
  }
</script>

<div class="list">
  <div class="count">
    <span>
      {features.length} result{features.length === 1 ? '' : 's'}{#if ui.userLocation} &middot; nearest first{/if}
    </span>
    {#if ui.savedIds.size > 0}
      <button
        class="saved-toggle"
        class:on={ui.savedOnly}
        onclick={() => setSavedOnly(!ui.savedOnly)}
        aria-pressed={ui.savedOnly}
        title={ui.savedOnly ? 'Showing saved only, tap to show all' : 'Show only saved places'}
      >
        <Icon name="star" size={13} fill={ui.savedOnly ? 'currentColor' : 'none'} />
        Saved ({ui.savedIds.size})
      </button>
    {/if}
  </div>
  {#if features.length === 0 && config.submit?.url && !ui.savedOnly}
    <div class="empty">
      <p>No matches here.</p>
      <button class="add-link" onclick={() => openSuggest(null)}>
        Business not listed? Ask us to add it
      </button>
    </div>
  {/if}
  <ul>
    {#each features as feature (feature.id)}
      {@const sv = ui.savedIds.has(feature.id)}
      <li class="row" class:active={ui.selected?.id === feature.id}>
        <button class="pick" onclick={() => select(feature)}>
          <span class="title">{fieldText(feature, titleField)}</span>
          {#each restFields as field (field)}
            {@const text = fieldText(feature, field)}
            {#if text}<span class="sub">{text}</span>{/if}
          {/each}
        </button>
        <button
          class="star"
          class:saved={sv}
          onclick={() => toggleSavedPlace(feature.id)}
          aria-pressed={sv}
          aria-label={sv
            ? `Remove ${fieldText(feature, titleField)} from saved`
            : `Save ${fieldText(feature, titleField)}`}
        >
          <Icon name="star" size={16} fill={sv ? 'currentColor' : 'none'} />
        </button>
      </li>
    {/each}
  </ul>
</div>

<style>
  .list {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .count {
    margin: 0;
    padding: 0.5rem 0.9rem;
    font-size: 0.8rem;
    color: var(--pub-muted, #5c5c5c);
    border-top: 1px solid var(--pub-border-soft);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }
  .saved-toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    border: 1px solid var(--pub-border, #d8dde4);
    border-radius: 999px;
    background: none;
    padding: 0.2rem 0.6rem;
    font-size: 0.76rem;
    font-weight: 600;
    color: var(--pub-muted, #5c5c5c);
    cursor: pointer;
    white-space: nowrap;
    transition: background var(--motion-duration), color var(--motion-duration);
  }
  .saved-toggle:hover {
    color: var(--civic-blue);
    border-color: var(--civic-blue);
  }
  .saved-toggle.on {
    background: var(--civic-blue-soft);
    border-color: var(--civic-blue);
    color: var(--civic-blue-deep);
  }
  .saved-toggle:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .empty {
    padding: 0.9rem;
    font-size: 0.85rem;
    color: var(--pub-muted, #5c5c5c);
  }
  .empty p {
    margin: 0 0 0.35rem;
  }
  .add-link {
    border: none;
    background: none;
    padding: 0;
    font-family: var(--font-body, sans-serif);
    font-size: 0.85rem;
    color: var(--civic-blue-link);
    text-decoration: underline;
    cursor: pointer;
    text-align: left;
  }
  .add-link:hover {
    color: var(--civic-blue-deep, #1e437e);
  }
  .add-link:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: var(--pub-radius-sm, 8px);
  }

  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    overflow-y: auto;
  }
  .row {
    display: flex;
    align-items: stretch;
    border-bottom: 1px solid var(--pub-border-soft);
  }
  .row.active {
    background: var(--civic-blue-soft);
    box-shadow: inset 3px 0 0 var(--civic-blue);
  }
  .pick {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    min-width: 0;
    text-align: left;
    border: none;
    background: none;
    padding: 0.5rem 0.9rem;
    cursor: pointer;
  }
  .row:hover {
    background: var(--pub-surface-2);
  }
  .star {
    flex: none;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.6rem;
    border: none;
    background: none;
    cursor: pointer;
    color: #b9c0c9;
  }
  .star:hover,
  .star.saved {
    color: var(--civic-blue);
  }
  .star:focus-visible,
  .pick:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .title {
    font-weight: 600;
    font-size: 0.92rem;
  }
  .sub {
    font-size: 0.82rem;
    color: var(--pub-muted);
  }

  /* Phones/tablets: roomier rows for touch */
  @media (max-width: 860px) {
    .pick {
      padding: 0.7rem 1rem;
      min-height: 48px;
      justify-content: center;
    }
    .star {
      width: 3rem;
    }
    .title {
      font-size: 1rem;
    }
    .sub {
      font-size: 0.88rem;
    }
  }
</style>
