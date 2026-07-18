<script lang="ts">
  import { loadAsync } from '../loadJson.svelte';
  import OfflineBadge from '../OfflineBadge.svelte';
  import { validateCivicClerkEvents, type CivicClerkEvent } from './civicClerk';

  const PORTAL = 'https://burtonmi.portal.civicclerk.com';
  const API = 'https://burtonmi.api.civicclerk.com/v1/Events';

  function query(filter: string, order: string): string {
    const params = new URLSearchParams({
      $top: '15',
      $orderby: `startDateTime ${order}`,
      $filter: filter,
    });
    return `${API}?${params.toString()}`;
  }

  // Live CivicClerk API (not a committed file, so loadAsync not loadJson); a
  // null result = the fetch failed and the offline/error state shows.
  async function responseJson(response: Response): Promise<unknown> {
    if (!response.ok) throw new Error(`CivicClerk request failed (${response.status})`);
    return response.json();
  }

  const meetings = loadAsync<{ upcoming: CivicClerkEvent[]; recent: CivicClerkEvent[] } | null>(async () => {
    const now = new Date().toISOString();
    const [upcomingRaw, recentRaw] = await Promise.all([
      fetch(query(`startDateTime ge ${now}`, 'asc')).then(responseJson),
      fetch(query(`startDateTime lt ${now}`, 'desc')).then(responseJson),
    ]);
    return {
      upcoming: validateCivicClerkEvents(upcomingRaw, 'upcoming').slice(0, 12),
      recent: validateCivicClerkEvents(recentRaw, 'recent').slice(0, 12),
    };
  }, null);
  const upcoming = $derived(meetings.data?.upcoming ?? []);
  const recent = $derived(meetings.data?.recent ?? []);
  const loading = $derived(meetings.loading);
  const failed = $derived(!meetings.loading && !meetings.data);

  // Times are stored as the local clock time with a Z suffix, so render in UTC to
  // show the intended wall-clock time (no timezone shift).
  function fmt(iso: string): string {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    const date = d.toLocaleDateString('en-US', {
      timeZone: 'UTC',
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
    const time = d.toLocaleTimeString('en-US', {
      timeZone: 'UTC',
      hour: 'numeric',
      minute: '2-digit',
    });
    return `${date} · ${time}`;
  }
  const eventUrl = (id: number) => `${PORTAL}/event/${id}/overview`;
</script>

<div class="cc">
  <OfflineBadge label="Offline: meeting list may be out of date" />
  <p class="intro">
    Live agendas, minutes, and meeting videos from the City's official
    <a href={PORTAL} target="_blank" rel="noopener noreferrer">CivicClerk portal</a>. Select a meeting
    to open its agenda packet, minutes, and video.
  </p>

  {#if loading}
    <p class="state">Loading meetings&hellip;</p>
  {:else if failed}
    <p class="state">
      Meetings couldn't be loaded right now.
      <a href={PORTAL} target="_blank" rel="noopener noreferrer">Open the meetings portal</a>.
    </p>
  {:else}
    {#if upcoming.length}
      <h3>Upcoming meetings</h3>
      <ul class="events">
        {#each upcoming as e (e.id)}
          <li>
            <div class="when">{fmt(e.startDateTime)}</div>
            <div class="what">
              <a href={eventUrl(e.id)} target="_blank" rel="noopener noreferrer">{e.eventName}</a>
              {#if e.categoryName && e.categoryName !== e.eventName}<span class="cat">{e.categoryName}</span>{/if}
            </div>
          </li>
        {/each}
      </ul>
    {/if}

    {#if recent.length}
      <h3>Recent meetings</h3>
      <ul class="events">
        {#each recent as e (e.id)}
          <li>
            <div class="when">{fmt(e.startDateTime)}</div>
            <div class="what">
              <a href={eventUrl(e.id)} target="_blank" rel="noopener noreferrer">{e.eventName}</a>
              <span class="tags">
                {#if e.agendaId}<span class="tag">Agenda &amp; minutes</span>{/if}
                {#if e.mediaStreamPath}<span class="tag video">&#9654; Video</span>{/if}
              </span>
            </div>
          </li>
        {/each}
      </ul>
    {/if}

    <p class="note">
      Source: City of Burton CivicClerk portal. Showing the next and most recent meetings.
      <a href={PORTAL} target="_blank" rel="noopener noreferrer">See all meetings &amp; documents</a>.
    </p>
  {/if}
</div>

<style>
  .cc {
    max-width: 680px;
  }
  .intro {
    line-height: 1.6;
    margin: 0 0 1rem;
  }
  .cc :global(h3),
  .cc h3 {
    font-family: var(--font-head, sans-serif);
    color: var(--civic-blue, #2c57a0);
    font-size: 1.05rem;
    margin: 1.3rem 0 0.4rem;
  }
  .state {
    color: var(--pub-muted, #5c5c5c);
    padding: 0.6rem 0;
  }
  .events {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .events li {
    display: flex;
    gap: 0.9rem;
    padding: 0.55rem 0.2rem;
    border-bottom: 1px solid var(--pub-border, #eef1f5);
    align-items: baseline;
  }
  .when {
    flex: 0 0 11rem;
    color: var(--pub-muted);
    font-size: 0.85rem;
    font-variant-numeric: tabular-nums;
  }
  .what {
    min-width: 0;
  }
  .what a {
    color: var(--civic-blue-link, #386fc5);
    font-weight: 600;
  }
  .cat {
    display: inline-block;
    margin-left: 0.5rem;
    font-size: 0.72rem;
    color: var(--pub-muted, #5c5c5c);
  }
  .tags {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-left: 0.5rem;
  }
  .tag {
    font-size: 0.7rem;
    background: var(--civic-blue-soft, #d7e1f3);
    color: var(--civic-blue-deep, #1e437e);
    padding: 0.1rem 0.45rem;
    border-radius: 999px;
    white-space: nowrap;
  }
  .tag.video {
    background: #fde7e7;
    color: #b3261e;
  }
  .note {
    margin: 1.2rem 0 0;
    font-size: 0.78rem;
    color: var(--pub-muted, #5c5c5c);
    line-height: 1.4;
  }
  @media (max-width: 560px) {
    .events li {
      flex-direction: column;
      gap: 0.15rem;
    }
    .when {
      flex-basis: auto;
    }
  }
</style>
