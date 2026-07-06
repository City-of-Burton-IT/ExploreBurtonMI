<script lang="ts">
  import { onMount } from 'svelte';
  import { dataFetch } from '../remote';
  import {
    activeOpsItems,
    statusMeta,
    validateOpsStatusBundle,
    type OpsItem,
    type OpsStatusKey,
  } from './opsStatus';
  import { safeHref } from '../templates';
  import Icon from '../Icon.svelte';

  // Icon registry names per status key (icons.ts).
  const STATUS_ICON: Record<OpsStatusKey, string> = {
    'in-progress': 'activity',
    scheduled: 'calendar',
    complete: 'check-circle',
    standby: 'pause-circle',
  };

  let items = $state<OpsItem[]>([]);
  let updated = $state<string>('');
  let loading = $state(true);

  onMount(async () => {
    try {
      const r = await dataFetch('ops-status.json');
      if (r.ok) {
        const b = validateOpsStatusBundle(await r.json());
        items = b.items ?? [];
        updated = b.updated ?? '';
      }
    } catch {
      items = [];
    }
    loading = false;
  });

  const shown = $derived(activeOpsItems(items));
</script>

<div class="ops">
  <p class="intro">
    Current status of the city's seasonal services like leaf pickup, yard waste, snow plowing,
    and hydrant flushing. Out-of-season services are hidden until they start.
  </p>

  {#if loading}
    <p class="state">Loading the latest status&hellip;</p>
  {:else if shown.length === 0}
    <p class="state">No seasonal services are active right now. Check back as the seasons change.</p>
  {:else}
    <ul class="list">
      {#each shown as item (item.id)}
        {@const meta = statusMeta(item.status)}
        <li>
          <Icon name={STATUS_ICON[meta.icon]} size={22} class="icon" style={`color: ${meta.color}`} />
          <div class="body">
            <div class="head">
              <span class="service">{item.service}</span>
              <span class="chip" style:background={meta.color}>{meta.label}</span>
            </div>
            <p class="detail">{item.detail}</p>
            {#if item.link}
              <a class="link" href={safeHref(item.link.href)} target="_blank" rel="noopener noreferrer"
                >{item.link.text}</a
              >
            {/if}
          </div>
        </li>
      {/each}
    </ul>
  {/if}

  {#if updated}
    <p class="note">Updated {updated}. Maintained by the City of Burton.</p>
  {/if}
</div>

<style>
  .ops {
    max-width: 640px;
  }
  .intro {
    line-height: 1.6;
    margin: 0 0 1rem;
  }
  .state {
    color: var(--pub-muted, #5c5c5c);
    font-size: 0.95rem;
    margin: 0.8rem 0;
  }
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .list li {
    display: flex;
    align-items: flex-start;
    gap: 0.7rem;
    padding: 0.8rem 0.2rem;
    border-bottom: 1px solid var(--pub-border, #eef1f5);
  }
  /* Icon.svelte renders the <svg> in its own component scope; :global() reaches
     through to it (same idiom as Guide.svelte's `.sectionnav button :global(.gicon)`). */
  .list :global(.icon) {
    flex: 0 0 auto;
    margin-top: 0.1rem;
  }
  .body {
    flex: 1 1 auto;
    min-width: 0;
  }
  .head {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem 0.7rem;
  }
  .service {
    font-weight: 700;
    color: var(--pub-ink, #2c2c2c);
  }
  .chip {
    color: #fff;
    font-weight: 700;
    font-size: 0.74rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    padding: 0.16rem 0.55rem;
    border-radius: 999px;
    white-space: nowrap;
  }
  .detail {
    margin: 0.35rem 0 0;
    line-height: 1.5;
    color: var(--pub-ink, #2c2c2c);
  }
  .link {
    display: inline-block;
    margin-top: 0.3rem;
    color: var(--civic-blue-link, #386fc5);
    font-weight: 600;
    font-size: 0.9rem;
  }
  .note {
    margin: 1.2rem 0 0;
    font-size: 0.78rem;
    color: var(--pub-muted, #5c5c5c);
    line-height: 1.4;
  }
</style>
