<script lang="ts">
  import { fetchStatus, type StatusResult, type TrackKind } from './track';

  // The read-only status-lookup endpoint (config.status.url). Empty when the
  // read flow has not been wired yet -> the page renders the not-found state.
  let { statusUrl }: { statusUrl: string } = $props();

  // Parse the token + kind out of the hash query (#status?t=<token>&k=<kind>).
  function parse(): { token: string; kind: TrackKind } | null {
    const h = location.hash.replace(/^#status\??/, '');
    const p = new URLSearchParams(h);
    const token = p.get('t');
    if (!token) return null;
    const k = p.get('k');
    return { token, kind: k === 'listing' ? 'listing' : 'report' };
  }

  let phase = $state<'loading' | 'done'>('loading');
  let result = $state<StatusResult | null>(null);

  $effect(() => {
    const q = parse();
    if (!q || !statusUrl) {
      phase = 'done';
      result = { found: false };
      return;
    }
    phase = 'loading';
    fetchStatus(statusUrl, q.token, q.kind).then((r) => {
      result = r;
      phase = 'done';
    });
  });
</script>

<section class="status" aria-label="Request status">
  <h2>Request status</h2>
  {#if phase === 'loading'}
    <p class="muted">Checking&hellip;</p>
  {:else if result?.found}
    <p class="stage">{result.stage}</p>
    {#if result.recap}<p class="recap">{result.recap}</p>{/if}
    {#if result.publicNote}<p class="note">{result.publicNote}</p>{/if}
    {#if result.updatedAt}<p class="updated">Last updated {result.updatedAt}</p>{/if}
  {:else}
    <p class="muted">
      We couldn&rsquo;t find a request for that link. Check the link from your
      confirmation, or contact the city.
    </p>
  {/if}
</section>

<style>
  .status {
    max-width: 42rem;
    margin: 0 auto;
    padding: 1.5rem 1rem 2.5rem;
    background: var(--pub-surface);
  }
  h2 {
    font-family: var(--font-head);
    color: var(--civic-blue);
    margin: 0 0 1rem;
  }
  .stage {
    font-family: var(--font-head);
    font-size: 1.5rem;
    color: var(--civic-blue-deep, #1e437e);
    margin: 0 0 0.5rem;
  }
  .recap {
    color: var(--pub-ink);
    margin: 0 0 0.5rem;
  }
  .note {
    color: var(--pub-ink);
    border-left: 3px solid var(--civic-blue);
    padding-left: 0.75rem;
    margin: 0 0 0.75rem;
  }
  .updated,
  .muted {
    color: var(--pub-muted, #5c5c5c);
    font-size: 0.9rem;
  }
</style>
