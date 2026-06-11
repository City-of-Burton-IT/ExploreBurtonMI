<script lang="ts">
  import type { InfoPanel, InfoChart } from './types';
  import { safeHref } from './templates';
  import { formatValue } from './charts/scale';
  import { formatDataAsOf } from './freshness';
  import { reportOutdatedMailto } from './feedback';
  import StatCard from './StatCard.svelte';
  import Donut from './charts/Donut.svelte';
  import Bars from './charts/Bars.svelte';
  import TrendLine from './charts/TrendLine.svelte';
  import CompareBars from './charts/CompareBars.svelte';
  import InfoTable from './InfoTable.svelte';
  import TaxEstimator from './TaxEstimator.svelte';

  let {
    panel,
    loading = false,
    description,
  }: { panel: InfoPanel | null; loading?: boolean; description?: string } = $props();

  let explainerOpen = $state(false);

  // Resident-facing "Data as of {Month YYYY}" freshness label (null when the panel
  // carries no lastUpdated, so the line is simply omitted).
  const dataAsOf = $derived(formatDataAsOf(panel?.lastUpdated));

  // Accessible plain-data fallback for any chart: a collapsible table with the
  // same numbers the SVG/bars show. Helps screen-reader and no-JS-render users,
  // and lets anyone read exact values. One generic builder covers every type.
  function chartTable(chart: InfoChart): { headers: string[]; rows: string[][] } | null {
    const unit = chart.unit ?? '';
    if (chart.type === 'bars' || chart.type === 'donut') {
      const series = chart.series ?? [];
      if (!series.length) return null;
      return { headers: ['Category', 'Value'], rows: series.map((s) => [s.label, formatValue(s.value, unit)]) };
    }
    if (chart.type === 'trend') {
      if (chart.lines?.length) {
        const xs: string[] = [];
        for (const ln of chart.lines) for (const p of ln.points) if (!xs.includes(p.x)) xs.push(p.x);
        return {
          headers: ['Period', ...chart.lines.map((l) => l.label)],
          rows: xs.map((x) => [
            x,
            ...chart.lines!.map((l) => {
              const pt = l.points.find((p) => p.x === x);
              return pt ? formatValue(pt.y, unit) : '';
            }),
          ]),
        };
      }
      const points = chart.points ?? [];
      if (!points.length) return null;
      return { headers: ['Period', 'Value'], rows: points.map((p) => [p.x, formatValue(p.y, unit)]) };
    }
    if (chart.type === 'compare') {
      const rows = chart.rows ?? [];
      if (!rows.length) return null;
      const places = rows[0].values.map((v) => v.name);
      return {
        headers: ['Metric', ...places],
        rows: rows.map((r) => [r.label, ...r.values.map((v) => formatValue(v.value, r.unit ?? ''))]),
      };
    }
    return null;
  }

  // Download a chart's data table as a CSV file (same numbers as the table).
  function csvSlug(s: string): string {
    return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'chart';
  }
  function downloadCsv(chart: InfoChart): void {
    const t = chartTable(chart);
    if (!t) return;
    const esc = (s: string) => (/[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s);
    const csv = [t.headers, ...t.rows].map((r) => r.map(esc).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `${csvSlug(chart.title)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }
</script>

<section class="info" aria-label={panel?.title ?? 'Information'}>
  {#if loading}
    <p class="state">Loading&hellip;</p>
  {:else if !panel}
    <p class="state">This information is temporarily unavailable. Please check back soon.</p>
  {:else}
    <header class:has-logo={panel.logo}>
      {#if panel.logo}
        <!-- Hidden gracefully if the file is missing, so referencing a
             not-yet-added logo never shows a broken-image icon. -->
        <img
          class="panel-logo"
          src={panel.logo}
          alt="{panel.title} logo"
          onerror={(e) => ((e.currentTarget as HTMLImageElement).style.display = 'none')}
        />
      {/if}
      <div class="header-text">
        <h2>{panel.title}</h2>
        {#if panel.subtitle}
          <p class="subtitle">{panel.subtitle}</p>
        {:else if description}
          <p class="subtitle">{description}</p>
        {/if}
      </div>
    </header>

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
      <aside class="summary" aria-label="What this means">
        <h3>{panel.summary.heading ?? 'What this means for you'}</h3>
        {#each panel.summary.body as para}
          <p>{para}</p>
        {/each}
      </aside>
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
          {@const dt = chartTable(chart)}
          <figure class="chart">
            <figcaption>{chart.title}</figcaption>
            {#if chart.type === 'donut'}
              <Donut series={chart.series ?? []} unit={chart.unit} />
            {:else if chart.type === 'bars'}
              <Bars series={chart.series ?? []} unit={chart.unit} />
            {:else if chart.type === 'trend'}
              <TrendLine
                points={chart.points ?? []}
                unit={chart.unit}
                markers={chart.markers}
                lines={chart.lines}
              />
            {:else if chart.type === 'compare'}
              <CompareBars rows={chart.rows ?? []} citiesLede={chart.citiesLede} />
            {/if}
            {#if dt}
              <details class="data-table">
                <summary>View data table</summary>
                <table>
                  <caption class="sr-only">{chart.title}</caption>
                  <thead>
                    <tr>{#each dt.headers as h}<th scope="col">{h}</th>{/each}</tr>
                  </thead>
                  <tbody>
                    {#each dt.rows as r}
                      <tr>
                        <th scope="row">{r[0]}</th>
                        {#each r.slice(1) as cell}<td>{cell}</td>{/each}
                      </tr>
                    {/each}
                  </tbody>
                </table>
                <button class="csv-btn" type="button" onclick={() => downloadCsv(chart)}>
                  Download CSV
                </button>
              </details>
            {/if}
          </figure>
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
      <div class="explainer">
        <button
          class="explainer-toggle"
          aria-expanded={explainerOpen}
          onclick={() => (explainerOpen = !explainerOpen)}
        >
          <span class="ex-icon" aria-hidden="true">{explainerOpen ? '−' : '+'}</span>
          {panel.explainer.title}
        </button>
        {#if explainerOpen}
          <div class="explainer-body">
            {#if panel.explainer.intro}<p class="ex-intro">{panel.explainer.intro}</p>{/if}
            {#each panel.explainer.items as item (item.term)}
              <details class="ex-card">
                <summary>{item.term}</summary>
                <p>{item.body}</p>
              </details>
            {/each}
            {#if panel.explainer.source}<p class="ex-source">{panel.explainer.source}</p>{/if}
          </div>
        {/if}
      </div>
    {/if}

    <hr />
    <footer>
      {#if panel.source}<p class="source">Source: {panel.source}</p>{/if}
      {#if dataAsOf}<p class="freshness">Data as of {dataAsOf}</p>{/if}
      {#if panel.links?.length}
        <ul class="links">
          {#each panel.links as link (link.href)}
            <li><a href={safeHref(link.href)} target="_blank" rel="noopener noreferrer">{link.text}</a></li>
          {/each}
        </ul>
      {/if}
      {#if panel.notes?.length}
        {#each panel.notes as note}
          <p class="note">{note}</p>
        {/each}
      {/if}
      <p class="report">
        <a href={reportOutdatedMailto(panel.title)}>Report outdated information</a>
      </p>
    </footer>
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
  header.has-logo {
    display: flex;
    align-items: center;
    gap: 0.85rem;
  }
  .panel-logo {
    height: 56px;
    width: auto;
    flex: none;
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
  .summary {
    background: var(--civic-blue-tint, #eef3fb);
    border-left: 4px solid var(--civic-blue, #2c57a0);
    border-radius: var(--pub-radius-sm, 6px);
    padding: 0.85rem 1.1rem;
    margin: 0 0 1.4rem;
  }
  .summary h3 {
    margin: 0 0 0.4rem;
    font-family: var(--font-head, sans-serif);
    font-weight: 700;
    font-size: 1.02rem;
    color: var(--civic-blue, #2c57a0);
  }
  .summary p {
    margin: 0.4rem 0 0;
    font-size: 0.92rem;
    line-height: 1.5;
    color: #333;
  }
  .summary p:first-of-type {
    margin-top: 0;
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
  .data-table {
    margin-top: 0.6rem;
  }
  .data-table > summary {
    font-size: 0.78rem;
    color: var(--civic-blue-link, #1a4b8f);
    cursor: pointer;
    width: fit-content;
  }
  .data-table > summary:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: 4px;
  }
  .data-table table {
    border-collapse: collapse;
    margin-top: 0.5rem;
    font-size: 0.8rem;
    width: 100%;
  }
  .data-table th,
  .data-table td {
    text-align: left;
    padding: 0.28rem 0.6rem 0.28rem 0;
    border-bottom: 1px solid var(--pub-border, #e3e3e3);
    white-space: nowrap;
  }
  .data-table thead th {
    color: var(--pub-muted, #5c5c5c);
    font-weight: 700;
  }
  .data-table tbody th {
    font-weight: 600;
    white-space: normal;
  }
  .data-table td {
    font-variant-numeric: tabular-nums;
  }
  .csv-btn {
    margin-top: 0.6rem;
    border: 1px solid var(--civic-blue, #2c57a0);
    background: #fff;
    color: var(--civic-blue, #2c57a0);
    border-radius: var(--pub-radius-sm, 8px);
    padding: 0.3rem 0.7rem;
    font-family: var(--font-body, sans-serif);
    font-weight: 700;
    font-size: 0.76rem;
    cursor: pointer;
  }
  .csv-btn:hover {
    background: var(--civic-blue-soft, #d7e1f3);
  }
  .csv-btn:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
  .tables {
    display: grid;
    gap: 1.4rem;
    margin-top: 1.6rem;
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
  .explainer {
    margin-top: 1.8rem;
  }
  .explainer-toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--civic-blue, #2c57a0);
    color: #fff;
    border: none;
    border-radius: var(--pub-radius-sm, 6px);
    padding: 0.6rem 1rem;
    font-family: var(--font-head, sans-serif);
    font-weight: 600;
    font-size: 0.95rem;
    cursor: pointer;
  }
  .explainer-toggle:hover {
    background: var(--civic-blue-link, #1a4b8f);
  }
  .ex-icon {
    font-size: 1.1rem;
    line-height: 1;
    font-weight: 700;
  }
  .explainer-body {
    margin-top: 0.8rem;
    animation: ex-reveal 0.22s ease;
  }
  @keyframes ex-reveal {
    from { opacity: 0; transform: translateY(-4px); }
    to { opacity: 1; transform: translateY(0); }
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
    background: #fafbfd;
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
    color: #333;
  }
  .ex-source {
    margin: 0.6rem 0 0;
    font-size: 0.72rem;
    color: var(--pub-muted, #5c5c5c);
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
  .freshness {
    margin: 0.25rem 0 0;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--pub-muted, #5c5c5c);
  }
  .note {
    margin: 0.4rem 0 0;
    font-size: 0.72rem;
    line-height: 1.35;
    color: var(--pub-muted, #5c5c5c);
  }
  .report {
    margin: 0.6rem 0 0;
    font-size: 0.8rem;
  }
  .report a {
    color: var(--civic-blue-link, #386fc5);
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
