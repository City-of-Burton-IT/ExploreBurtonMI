<script lang="ts">
  import type { DashboardContext } from './types';
  import { dashboardStatusLabel } from './dashboard/dashboardContext';
  import { safeHref } from './templates';

  let {
    title,
    subtitle,
    group,
    logo,
    context,
  }: {
    title: string;
    subtitle?: string;
    group?: string | null;
    logo?: string;
    context?: DashboardContext;
  } = $props();
</script>

<header class:has-logo={logo}>
  {#if logo}
    <!-- Hidden gracefully if the file is missing, so referencing a
         not-yet-added logo never shows a broken-image icon. -->
    <img
      class="panel-logo"
      src={logo}
      alt="{title} logo"
      onerror={(e) => ((e.currentTarget as HTMLImageElement).style.display = 'none')}
    />
  {/if}
  <div class="header-text">
    {#if group}<p class="group-crumb">{group}</p>{/if}
    <h2>{title}</h2>
    {#if subtitle}
      <p class="subtitle">{subtitle}</p>
    {/if}
    {#if context}
      <section class="context" aria-label="Dashboard data context">
        <h3>About this data</h3>
        <dl>
          <div class="context-row">
            <dt>This covers</dt>
            <dd>{context.scope}</dd>
          </div>
          <div class="context-row">
            <dt>Information type</dt>
            <dd>{dashboardStatusLabel(context.status)}</dd>
          </div>
          <div class="context-row">
            <dt>Time period</dt>
            <dd>{context.asOf}</dd>
          </div>
          {#if context.sourceLinks?.length}
            <div class="context-row source-row">
              <dt>Official sources</dt>
              <dd>
                <ul>
                  {#each context.sourceLinks as link (link.href)}
                    <li>
                      <a href={safeHref(link.href)} target="_blank" rel="noopener noreferrer">
                        {link.text}
                      </a>
                    </li>
                  {/each}
                </ul>
              </dd>
            </div>
          {/if}
        </dl>
      </section>
    {/if}
  </div>
</header>

<style>
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
    color: var(--pub-muted);
    font-size: 0.95rem;
  }
  .group-crumb {
    margin: 0 0 0.1rem;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--pub-muted, #6b7280);
  }
  .context {
    max-width: 48rem;
    margin: 0.65rem 0 0;
    border: 1px solid var(--pub-border);
    border-radius: var(--pub-radius-sm, 8px);
    background: var(--pub-surface-2);
    color: var(--pub-ink);
    overflow: hidden;
  }
  .context h3 {
    margin: 0;
    padding: 0.42rem 0.65rem 0.3rem;
    color: var(--pub-ink);
    font-family: var(--font-head, sans-serif);
    font-size: 0.82rem;
    font-weight: 700;
  }
  .context dl {
    margin: 0;
  }
  .context-row {
    display: grid;
    grid-template-columns: 8.2rem minmax(0, 1fr);
    gap: 0.65rem;
    padding: 0.34rem 0.65rem;
    border-top: 1px solid var(--pub-border);
    font-size: 0.82rem;
    line-height: 1.35;
  }
  .context dt {
    color: var(--pub-muted);
    font-weight: 700;
  }
  .context dd {
    min-width: 0;
    margin: 0;
    color: var(--pub-ink);
  }
  .source-row ul {
    display: flex;
    flex-wrap: wrap;
    gap: 0.2rem 0.8rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .source-row a {
    color: var(--civic-blue-link);
    font-weight: 600;
    text-underline-offset: 0.12em;
  }
  .source-row a:focus-visible {
    outline: none;
    border-radius: 2px;
    box-shadow: var(--pub-focus-ring);
  }
  @media (max-width: 520px) {
    .context-row {
      grid-template-columns: 7.1rem minmax(0, 1fr);
      gap: 0.45rem;
      padding: 0.32rem 0.55rem;
      font-size: 0.78rem;
    }
  }
</style>
