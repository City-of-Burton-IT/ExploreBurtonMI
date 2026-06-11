<script lang="ts">
  import type { AppConfig } from './types';
  import type { FacetCounts } from './filter';
  import { ui, toggleFacet, clearFacet } from './store.svelte';

  let { config, facetCounts }: { config: AppConfig; facetCounts: FacetCounts } = $props();

  function valuesFor(field: string): string[] {
    const counts = facetCounts[field] ?? {};
    const selected = ui.selections[field] ?? [];
    const all = new Set<string>([...Object.keys(counts), ...selected]);
    return [...all].sort((a, b) => a.localeCompare(b));
  }

  function isSelected(field: string, value: string): boolean {
    return (ui.selections[field] ?? []).includes(value);
  }
</script>

<div class="facets">
  {#each Object.entries(config.facets) as [field, facet] (field)}
    {@const selectedCount = (ui.selections[field] ?? []).length}
    <section class="facet">
      <div class="facet-head">
        <h3>{facet.title}</h3>
        {#if selectedCount > 0}
          <button class="clear" onclick={() => clearFacet(field)}>clear</button>
        {/if}
      </div>
      <ul>
        {#each valuesFor(field) as value (value)}
          {@const count = facetCounts[field]?.[value] ?? 0}
          {@const disabled = count === 0 && !isSelected(field, value)}
          <li>
            <label
              class:disabled
              title={disabled ? 'No matching results with the current filters' : null}
            >
              <input
                type="checkbox"
                checked={isSelected(field, value)}
                onchange={() => toggleFacet(field, value)}
              />
              <span class="value">{value}</span>
              <span class="count">{count}</span>
            </label>
          </li>
        {/each}
      </ul>
    </section>
  {/each}
</div>

<style>
  .facets {
    padding: 0.75rem 0.9rem;
  }
  .facet-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
  }
  h3 {
    margin: 0.5rem 0 0.4rem;
    font-family: var(--font-head);
    font-weight: 700;
    font-size: 0.95rem;
    color: var(--civic-blue);
  }
  .clear {
    border: none;
    background: none;
    color: var(--civic-blue-link);
    cursor: pointer;
    font-size: 0.8rem;
  }
  input[type='checkbox'] {
    accent-color: var(--civic-blue);
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.2rem 0;
    font-size: 0.9rem;
    cursor: pointer;
  }
  /* Disabled = no matches under the current filters. Use a muted-but-AA-legible
     color (>= 4.5:1 on white) instead of opacity (which failed contrast), plus a
     not-allowed cursor and a title to explain why. */
  label.disabled,
  label.disabled .count {
    color: var(--pub-muted, #5c5c5c);
    cursor: not-allowed;
  }
  .value {
    flex: 1 1 auto;
  }
  .count {
    color: var(--pub-muted, #5c5c5c);
    font-variant-numeric: tabular-nums;
  }

  /* Phones/tablets: larger touch targets */
  @media (max-width: 860px) {
    label {
      padding: 0.5rem 0;
      font-size: 0.98rem;
    }
    input[type='checkbox'] {
      width: 1.1rem;
      height: 1.1rem;
    }
  }
</style>
