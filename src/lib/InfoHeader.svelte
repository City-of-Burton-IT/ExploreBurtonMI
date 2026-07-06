<script lang="ts">
  let {
    title,
    subtitle,
    group,
    logo,
  }: {
    title: string;
    subtitle?: string;
    group?: string | null;
    logo?: string;
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
</style>
