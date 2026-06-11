<script lang="ts">
  import { onMount } from 'svelte';
  import { dataFetch } from '../remote';
  import {
    activeOpsItems,
    statusMeta,
    type OpsStatusBundle,
    type OpsItem,
    type OpsStatusKey,
  } from './opsStatus';
  import { safeHref } from '../templates';

  // Lucide (https://lucide.dev, ISC/MIT) inner SVG markup per status key.
  const STATUS_ICON: Record<OpsStatusKey, string> = {
    'in-progress':
      '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>',
    scheduled:
      '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
    complete: '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    standby:
      '<circle cx="12" cy="12" r="10"/><line x1="10" x2="10" y1="15" y2="9"/><line x1="14" x2="14" y1="15" y2="9"/>',
  };

  let items = $state<OpsItem[]>([]);
  let updated = $state<string>('');
  let loading = $state(true);

  onMount(async () => {
    try {
      const r = await dataFetch('ops-status.json');
      if (r.ok) {
        const b = (await r.json()) as OpsStatusBundle;
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
    Current status of the city's seasonal services &mdash; leaf pickup, yard waste, snow plowing,
    hydrant flushing, and the like. Out-of-season services are hidden until they start.
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
          <svg
            class="icon"
            style:color={meta.color}
            viewBox="0 0 24 24"
            width="22"
            height="22"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true">{@html STATUS_ICON[meta.icon]}</svg
          >
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
  .icon {
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
