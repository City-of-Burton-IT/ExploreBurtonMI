<script lang="ts">
  import type { InfoPanel } from './infoPanel';
  import { reportOutdatedMailto } from '../feedback';
  import { formatDataAsOf } from '../freshness';
  import { safeHref } from '../templates';

  let { panel }: { panel: InfoPanel } = $props();
  const dataAsOf = $derived(formatDataAsOf(panel.lastUpdated));
</script>

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
  <!-- Mirrors the Contact column of the burtonmi.gov footer so the two feel like
       one property. The address and main line are the City Hall values the
       website publishes; change both places together. -->
  <address class="city">
    <span class="city-name">City of Burton</span>
    <span>4303 S Center Rd, Burton, MI 48519</span>
    <a href="tel:+18107431500">(810) 743-1500</a>
    <a href="https://www.burtonmi.gov" target="_blank" rel="noopener noreferrer">burtonmi.gov</a>
  </address>
</footer>

<style>
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
  .city {
    margin: 1rem 0 0;
    padding-top: 0.7rem;
    border-top: 1px solid var(--pub-border, #e3e3e3);
    font-style: normal;
    font-size: 0.8rem;
    color: var(--pub-muted, #5c5c5c);
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem 1rem;
  }
  .city-name {
    font-family: var(--font-head, sans-serif);
    font-weight: 700;
    color: var(--civic-blue, #2c57a0);
  }
  .city a {
    color: var(--civic-blue-link, #386fc5);
  }
</style>
