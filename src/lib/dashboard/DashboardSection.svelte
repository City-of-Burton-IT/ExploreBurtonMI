<script lang="ts">
  import type { InfoChart, InfoSection, InfoStat, InfoTable as InfoTableData } from './infoPanel';
  import StatCard from '../StatCard.svelte';
  import InfoTable from '../InfoTable.svelte';
  import DashboardChart from './DashboardChart.svelte';

  let {
    section,
    stats,
    charts,
    tables,
  }: {
    section: InfoSection;
    stats: InfoStat[];
    charts: InfoChart[];
    tables: InfoTableData[];
  } = $props();
</script>

<section class="evidence" aria-labelledby="section-{section.heading.toLowerCase().replace(/[^a-z0-9]+/g, '-')}">
  <h3 id="section-{section.heading.toLowerCase().replace(/[^a-z0-9]+/g, '-')}">{section.heading}</h3>
  {#if stats.length}
    <div class="stats">
      {#each stats as stat (stat.id)}
        <StatCard {stat} />
      {/each}
    </div>
  {/if}
  {#if charts.length}
    <div class="charts">
      {#each charts as chart (chart.id)}
        <DashboardChart {chart} />
      {/each}
    </div>
  {/if}
  {#if tables.length}
    <div class="tables">
      {#each tables as table (table.id)}
        <InfoTable {table} />
      {/each}
    </div>
  {/if}
</section>

<style>
  .evidence {
    margin-top: 1.7rem;
    padding-top: 1rem;
    border-top: 1px solid var(--pub-border);
  }
  h3 {
    margin: 0 0 0.9rem;
    color: var(--civic-blue-deep);
    font-family: var(--font-head, sans-serif);
    font-size: 1.08rem;
    font-weight: 700;
  }
  .stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.8rem;
    margin-bottom: 1.2rem;
  }
  .charts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.4rem 2rem;
  }
  .tables {
    display: grid;
    gap: 1.4rem;
    margin-top: 1.4rem;
  }
  @media (max-width: 860px) {
    .charts {
      grid-template-columns: 1fr;
    }
  }
</style>
