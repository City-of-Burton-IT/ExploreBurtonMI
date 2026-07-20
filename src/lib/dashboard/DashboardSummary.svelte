<script lang="ts">
  import type { InfoSummary } from './infoPanel';

  let { summary }: { summary: InfoSummary } = $props();
</script>

<aside class="summary" aria-label="What this means">
  <h3>{summary.heading ?? 'What this means for you'}</h3>
  {#each summary.body as paragraph}
    <p>{paragraph}</p>
  {/each}
</aside>

<style>
  .summary {
    background: var(--pub-surface-2);
    border-left: 4px solid var(--pub-border);
    border-radius: var(--pub-radius-sm, 6px);
    padding: 0.85rem 1.1rem;
    margin: 0 0 1.4rem;
  }
  .summary h3 {
    margin: 0 0 0.4rem;
    font-family: var(--font-head, sans-serif);
    font-weight: 700;
    font-size: 1.02rem;
    color: var(--pub-ink);
  }
  .summary p {
    margin: 0.4rem 0 0;
    font-size: 0.92rem;
    line-height: 1.5;
    color: var(--pub-ink);
  }
  .summary p:first-of-type {
    margin-top: 0;
  }
</style>
