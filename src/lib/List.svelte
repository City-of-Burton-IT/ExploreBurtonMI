<script lang="ts">
  import type { AppConfig, PlaceFeature } from './types';
  import { ui, select } from './store.svelte';

  let { config, features }: { config: AppConfig; features: PlaceFeature[] } = $props();

  const titleField = $derived(config.list[0]);
  const restFields = $derived(config.list.slice(1));

  function fieldText(feature: PlaceFeature, field: string): string {
    const v = feature.properties[field];
    return v == null ? '' : Array.isArray(v) ? v.join(', ') : String(v);
  }
</script>

<div class="list">
  <p class="count">
    {features.length} result{features.length === 1 ? '' : 's'}{#if ui.userLocation} &middot; nearest first{/if}
  </p>
  <ul>
    {#each features as feature (feature.id)}
      <li>
        <button
          class:active={ui.selected?.id === feature.id}
          onclick={() => select(feature)}
        >
          <span class="title">{fieldText(feature, titleField)}</span>
          {#each restFields as field (field)}
            {@const text = fieldText(feature, field)}
            {#if text}<span class="sub">{text}</span>{/if}
          {/each}
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
    border-top: 1px solid #e5e5e5;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    overflow-y: auto;
  }
  button {
    display: flex;
    flex-direction: column;
    width: 100%;
    text-align: left;
    border: none;
    background: none;
    padding: 0.5rem 0.9rem;
    cursor: pointer;
    border-bottom: 1px solid #f0f0f0;
  }
  button:hover {
    background: #f5f7fa;
  }
  button.active {
    background: var(--civic-blue-soft);
    box-shadow: inset 3px 0 0 var(--civic-blue);
  }
  .title {
    font-weight: 600;
    font-size: 0.92rem;
  }
  .sub {
    font-size: 0.82rem;
    color: #666;
  }

  /* Phones/tablets: roomier rows for touch */
  @media (max-width: 860px) {
    button {
      padding: 0.7rem 1rem;
      min-height: 48px;
      justify-content: center;
    }
    .title {
      font-size: 1rem;
    }
    .sub {
      font-size: 0.88rem;
    }
  }
</style>
