<script lang="ts">
  import type { InfoPanel } from './types';
  import StatCard from './StatCard.svelte';
  import InfoTable from './InfoTable.svelte';
  import TaxEstimator from './TaxEstimator.svelte';
  import InfoHeader from './InfoHeader.svelte';
  import InfoExplainer from './InfoExplainer.svelte';
  import DashboardNav from './DashboardNav.svelte';
  import DashboardChart from './dashboard/DashboardChart.svelte';
  import DashboardFooter from './dashboard/DashboardFooter.svelte';
  import DashboardSummary from './dashboard/DashboardSummary.svelte';
  import type { DashboardItem } from './store.svelte';

  let {
    panel,
    loading = false,
    error = false,
    onRetry,
    description,
    group,
    prev,
    next,
  }: {
    panel: InfoPanel | null;
    loading?: boolean;
    error?: boolean;
    onRetry?: () => void;
    description?: string;
    group?: string | null;
    prev?: DashboardItem | null;
    next?: DashboardItem | null;
  } = $props();

</script>

<section class="info" aria-label={panel?.title ?? 'Information'}>
  {#if loading}
    <p class="state">Loading&hellip;</p>
  {:else if !panel}
    {#if error}
      <div class="state error-state" role="alert">
        <p>We couldn't load this dashboard. Check your connection and try again.</p>
        <button class="retry" type="button" onclick={() => onRetry?.()}>Retry</button>
      </div>
    {:else}
      <p class="state">This information is temporarily unavailable. Please check back soon.</p>
    {/if}
  {:else}
    <InfoHeader
      title={panel.title}
      subtitle={panel.subtitle || description}
      {group}
      logo={panel.logo}
    />

    {#if panel.draft}
      <p class="draft" role="note">
        {#if panel.draftNote}
          <strong>Draft.</strong> {panel.draftNote}
        {:else}
          <strong>Draft figures.</strong> These numbers are provisional and not yet final.
        {/if}
      </p>
    {/if}

    {#if panel.summary?.body?.length}
      <DashboardSummary summary={panel.summary} />
    {/if}

    {#if panel.stats?.length}
      <div class="stats">
        {#each panel.stats as stat (stat.label)}
          <StatCard {stat} />
        {/each}
      </div>
    {/if}

    {#if panel.estimator?.districts?.length}
      <TaxEstimator data={panel.estimator} />
    {/if}

    {#if panel.charts?.length}
      <div class="charts">
        {#each panel.charts as chart (chart.title)}
          <DashboardChart {chart} />
        {/each}
      </div>
    {/if}

    {#if panel.tables?.length}
      <div class="tables">
        {#each panel.tables as table (table.title)}
          <InfoTable {table} />
        {/each}
      </div>
    {/if}

    {#if panel.explainer?.items?.length}
      <InfoExplainer title={panel.explainer.title}>
        {#if panel.explainer.intro}<p class="ex-intro">{panel.explainer.intro}</p>{/if}
        {#each panel.explainer.items as item (item.term)}
          <details class="ex-card">
            <summary>{item.term}</summary>
            <p>{item.body}</p>
          </details>
        {/each}
        {#if panel.explainer.source}<p class="ex-source">{panel.explainer.source}</p>{/if}
      </InfoExplainer>
    {/if}

    {#if panel.methodology?.body}
      <InfoExplainer title={panel.methodology.title ?? 'How we measure this'}>
        <p class="ex-intro">{panel.methodology.body}</p>
      </InfoExplainer>
    {/if}

    <DashboardFooter {panel} />

    <DashboardNav {prev} {next} />
  {/if}
</section>

<style>
  .info {
    height: 100%;
    overflow-y: auto;
    padding: 1.4rem 1.8rem 2.4rem;
    width: 100%;
    box-sizing: border-box;
  }
  .state {
    color: var(--pub-muted, #5c5c5c);
    font-size: 1rem;
    padding: 2rem 0;
  }
  .error-state .retry {
    margin-top: 0.6rem;
    border: none;
    background: var(--civic-accent-bg);
    color: #fff;
    border-radius: 999px;
    padding: 0.45rem 1.1rem;
    font-family: var(--font-body, sans-serif);
    font-size: 0.9rem;
    font-weight: 700;
    cursor: pointer;
  }
  .error-state .retry:hover {
    background: var(--civic-accent-bg-hover);
  }
  .error-state .retry:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .draft {
    background: #fff6e6;
    border-left: 3px solid #e08a00;
    border-radius: var(--pub-radius-sm, 6px);
    padding: 0.6rem 0.8rem;
    font-size: 0.88rem;
    margin: 0 0 1.1rem;
  }
  .stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.8rem;
    margin-bottom: 1.4rem;
  }
  .charts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.4rem 2rem;
  }
  .tables {
    display: grid;
    gap: 1.4rem;
    margin-top: 1.6rem;
  }
  .ex-intro {
    margin: 0 0 0.7rem;
    font-size: 0.92rem;
    color: #444;
  }
  .ex-card {
    border: 1px solid #e2e6ee;
    border-left: 3px solid var(--civic-green, #4ea735);
    border-radius: var(--pub-radius-sm, 6px);
    padding: 0.55rem 0.85rem;
    margin-bottom: 0.55rem;
    background: var(--pub-surface-2);
  }
  .ex-card summary {
    font-family: var(--font-head, sans-serif);
    font-weight: 600;
    font-size: 0.92rem;
    color: var(--civic-blue, #2c57a0);
    cursor: pointer;
  }
  .ex-card p {
    margin: 0.5rem 0 0.1rem;
    font-size: 0.9rem;
    line-height: 1.5;
    color: var(--pub-ink);
  }
  .ex-source {
    margin: 0.6rem 0 0;
    font-size: 0.72rem;
    color: var(--pub-muted, #5c5c5c);
  }

  @media (max-width: 860px) {
    .info {
      padding: 1.1rem 1.1rem 2rem;
    }
    .charts {
      grid-template-columns: 1fr;
    }
  }
</style>
