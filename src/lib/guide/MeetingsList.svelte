<script lang="ts">
  import type { GuideMeetings } from '../types';
  import { nextMeetingDate } from './nextMeeting';

  let { meetings }: { meetings: GuideMeetings } = $props();

  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const todayISO = new Date().toISOString().slice(0, 10);
  const nextDate = $derived(nextMeetingDate(meetings.council, todayISO));

  function fmt(iso: string): string {
    const [y, m, d] = iso.split('-').map(Number);
    return `${MONTHS[m - 1]} ${d}, ${y}`;
  }
</script>

{#if meetings.intro}<p class="intro">{meetings.intro}</p>{/if}

<h3>City Council</h3>
<ul class="meetings">
  {#each meetings.council as m (m.date)}
    <li class:next={m.date === nextDate}>
      <span class="date">{fmt(m.date)}{#if m.alt} <abbr title="moved for a holiday or election">*</abbr>{/if}</span>
      <span class="time">{m.time}</span>
      {#if m.date === nextDate}<span class="badge">Next</span>{/if}
    </li>
  {/each}
</ul>

<h3>Boards &amp; Commissions</h3>
<ul class="boards">
  {#each meetings.boards as b (b.name)}
    <li><span class="bname">{b.name}</span><span class="bsched">{b.schedule}</span></li>
  {/each}
</ul>

<style>
  .intro {
    color: #555;
    font-size: 0.92rem;
  }
  h3 {
    font-family: var(--font-head, sans-serif);
    color: var(--civic-blue, #2c57a0);
    font-size: 1.05rem;
    margin: 1.3rem 0 0.6rem;
  }
  .meetings {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 0.4rem;
  }
  .meetings li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.7rem;
    border: 1px solid #e5e9ee;
    border-radius: var(--pub-radius-sm, 8px);
    font-size: 0.9rem;
  }
  .meetings li.next {
    border-color: var(--civic-green, #4ea735);
    background: var(--civic-green-soft, #d9f1dd);
  }
  .date {
    font-weight: 600;
    flex: 1 1 auto;
  }
  .time {
    color: #666;
    white-space: nowrap;
  }
  .badge {
    background: var(--civic-green, #4ea735);
    color: #fff;
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    border-radius: 999px;
    padding: 0.1rem 0.45rem;
  }
  abbr {
    text-decoration: none;
    color: var(--civic-green-deep, #1d7f2b);
    cursor: help;
  }
  .boards {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .boards li {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.4rem 0;
    border-bottom: 1px solid #f0f0f0;
    font-size: 0.92rem;
  }
  .bname {
    font-weight: 600;
  }
  .bsched {
    color: #666;
    white-space: nowrap;
  }
</style>
