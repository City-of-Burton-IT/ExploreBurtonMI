<script lang="ts">
  import type { GuideContacts } from '../types';
  import { safeTel, safeMailto } from '../templates';

  let { contacts }: { contacts: GuideContacts } = $props();
</script>

{#each contacts.groups as group (group.name)}
  <h3>{group.name}</h3>
  <ul class="people">
    {#each group.people as p (p.name + '\u0000' + p.title)}
      <li>
        <div class="who">
          <span class="name">{p.name}</span>
          <span class="role">{p.title}</span>
        </div>
        <div class="contact">
          {#if p.phone}
            {@const tel = safeTel(p.phone)}
            {#if tel}<a href={tel}>{p.phone}</a>{:else}<span>{p.phone}</span>{/if}
          {/if}
          {#if p.email}
            {@const mail = safeMailto(p.email)}
            {#if mail}<a href={mail}>{p.email}</a>{/if}
          {/if}
        </div>
        {#if p.committees?.length}
          <ul class="committees">
            {#each p.committees as c (c)}<li>{c}</li>{/each}
          </ul>
        {/if}
      </li>
    {/each}
  </ul>
{/each}

<style>
  h3 {
    font-family: var(--font-head, sans-serif);
    color: var(--civic-blue, #2c57a0);
    font-size: 1.05rem;
    margin: 1.4rem 0 0.6rem;
  }
  h3:first-child {
    margin-top: 0;
  }
  .people {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 0.7rem;
  }
  .people > li {
    border: 1px solid #e5e9ee;
    border-radius: var(--pub-radius, 10px);
    padding: 0.7rem 0.85rem;
  }
  .who {
    display: flex;
    flex-direction: column;
  }
  .name {
    font-weight: 700;
    color: var(--pub-ink, #2c2c2c);
  }
  .role {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--pub-muted, #5c5c5c);
  }
  .contact {
    display: flex;
    flex-wrap: wrap;
    gap: 0.2rem 0.9rem;
    margin-top: 0.3rem;
    font-size: 0.9rem;
  }
  .contact a {
    color: var(--civic-blue-link, #386fc5);
  }
  .committees {
    list-style: disc;
    margin: 0.4rem 0 0;
    padding-left: 1.1rem;
    font-size: 0.82rem;
    color: var(--pub-muted);
  }
</style>
