<script lang="ts">
  import type { DashboardAction, InfoSummary } from './infoPanel';
  import { safeHref } from '../templates';

  let {
    summary,
    responsibility,
    action,
  }: {
    summary: InfoSummary;
    responsibility: string;
    action: DashboardAction;
  } = $props();
</script>

<aside class="summary" aria-label="What this means">
  <h3>{summary.heading ?? 'What this means for you'}</h3>
  {#each summary.body as paragraph}
    <p>{paragraph}</p>
  {/each}
  <div class="summary-grid">
    <div>
      <h4>City responsibility</h4>
      <p>{responsibility}</p>
    </div>
    <div>
      <h4>What you can do</h4>
      {#if action.kind === 'link'}
        <p><a href={safeHref(action.href)} target={action.href.startsWith('#') ? undefined : '_blank'} rel={action.href.startsWith('#') ? undefined : 'noopener noreferrer'}>{action.text}</a></p>
      {:else}
        <p>{action.text}</p>
      {/if}
    </div>
  </div>
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
  .summary-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.8rem;
    margin-top: 0.8rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--pub-border);
  }
  .summary-grid h4 {
    margin: 0 0 0.25rem;
    color: var(--pub-muted);
    font-family: var(--font-body, sans-serif);
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.045em;
    text-transform: uppercase;
  }
  .summary-grid p {
    margin: 0;
  }
  .summary a {
    color: var(--civic-blue-link);
    font-weight: 700;
  }
  @media (max-width: 520px) {
    .summary {
      padding: 0.75rem 0.85rem;
    }
    .summary-grid {
      grid-template-columns: 1fr;
      gap: 0.65rem;
    }
  }
</style>
