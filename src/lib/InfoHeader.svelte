<script lang="ts">
  import type { DashboardContext } from './types';

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
      <ul class="context" aria-label="Dashboard data context">
        <li aria-label="Scope: {context.scope}"><span>Scope</span>{context.scope}</li>
        <li aria-label="Data status: {context.status[0].toUpperCase() + context.status.slice(1)}">
          <span>Status</span>{context.status[0].toUpperCase() + context.status.slice(1)}
        </li>
        <li aria-label="As of: {context.asOf}"><span>As of</span>{context.asOf}</li>
      </ul>
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
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    list-style: none;
    margin: 0.55rem 0 0;
    padding: 0;
  }
  .context li {
    display: inline-flex;
    align-items: baseline;
    gap: 0.3rem;
    border: 1px solid var(--pub-border);
    border-radius: 999px;
    background: var(--pub-surface-2);
    color: var(--pub-ink);
    padding: 0.22rem 0.55rem;
    font-size: 0.75rem;
    line-height: 1.25;
  }
  .context span {
    color: var(--pub-muted);
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.035em;
    text-transform: uppercase;
  }
  @media (max-width: 520px) {
    .context {
      gap: 0.28rem;
    }
    .context li {
      padding: 0.2rem 0.45rem;
      font-size: 0.7rem;
    }
  }
</style>
