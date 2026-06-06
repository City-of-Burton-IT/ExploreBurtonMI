<script lang="ts">
  import type { InfoPanel } from './types';
  import StatCard from './StatCard.svelte';
  import Donut from './charts/Donut.svelte';
  import Bars from './charts/Bars.svelte';
  import TrendLine from './charts/TrendLine.svelte';
  import CompareBars from './charts/CompareBars.svelte';

  let {
    panel,
    loading = false,
  }: { panel: InfoPanel | null; loading?: boolean } = $props();
</script>

<section class="info" aria-label={panel?.title ?? 'Information'}>
  {#if loading}
    <p class="state">Loading&hellip;</p>
  {:else if !panel}
    <p class="state">This information is temporarily unavailable. Please check back soon.</p>
  {:else}
    <header>
      <h2>{panel.title}</h2>
      {#if panel.subtitle}<p class="subtitle">{panel.subtitle}</p>{/if}
    </header>

    {#if panel.draft}
      <p class="draft" role="note">
        <strong>Sample figures.</strong> These numbers are placeholders for layout review and
        are not final published figures.
      </p>
    {/if}

    {#if panel.stats?.length}
      <div class="stats">
        {#each panel.stats as stat (stat.label)}
          <StatCard {stat} />
        {/each}
      </div>
    {/if}

    {#if panel.charts?.length}
      <div class="charts">
        {#each panel.charts as chart (chart.title)}
          <figure class="chart">
            <figcaption>{chart.title}</figcaption>
            {#if chart.type === 'donut'}
              <Donut series={chart.series ?? []} unit={chart.unit} />
            {:else if chart.type === 'bars'}
              <Bars series={chart.series ?? []} unit={chart.unit} />
            {:else if chart.type === 'trend'}
              <TrendLine points={chart.points ?? []} unit={chart.unit} />
            {:else if chart.type === 'compare'}
              <CompareBars rows={chart.rows ?? []} />
            {/if}
          </figure>
        {/each}
      </div>
    {/if}

    {#if panel.source || panel.links?.length || panel.notes?.length}
      <hr />
      <footer>
        {#if panel.source}<p class="source">Source: {panel.source}</p>{/if}
        {#if panel.links?.length}
          <ul class="links">
            {#each panel.links as link (link.href)}
              <li><a href={link.href} target="_blank" rel="noopener noreferrer">{link.text}</a></li>
            {/each}
          </ul>
        {/if}
        {#if panel.notes?.length}
          {#each panel.notes as note}
            <p class="note">{note}</p>
          {/each}
        {/if}
      </footer>
    {/if}
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
  header {
    margin-bottom: 1rem;
  }
  h2 {
    margin: 0;
    font-family: var(--font-head, sans-serif);
    font-weight: 700;
    font-size: 1.5rem;
    color: var(--civic-blue, #2c57a0);
  }
  .subtitle {
    margin: 0.15rem 0 0;
    color: #666;
    font-size: 0.95rem;
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
  .chart {
    margin: 0;
    min-width: 0;
  }
  figcaption {
    font-family: var(--font-head, sans-serif);
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--civic-blue, #2c57a0);
    margin-bottom: 0.7rem;
    padding-left: 0.5rem;
    border-left: 3px solid var(--civic-blue, #2c57a0);
  }
  hr {
    border: none;
    border-top: 2px dashed var(--civic-green, #4ea735);
    margin: 1.6rem 0 1rem;
  }
  .source {
    margin: 0;
    font-size: 0.8rem;
    color: var(--pub-muted, #5c5c5c);
  }
  .note {
    margin: 0.4rem 0 0;
    font-size: 0.72rem;
    line-height: 1.35;
    color: var(--pub-muted, #5c5c5c);
  }
  .links {
    list-style: none;
    margin: 0.5rem 0 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 1.2rem;
  }
  .links a {
    color: var(--civic-blue-link, #1a4b8f);
    font-size: 0.9rem;
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
