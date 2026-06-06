<script lang="ts">
  import type { GuideBundle, GuideSectionMeta } from '../types';
  import ContactsList from './ContactsList.svelte';
  import MeetingsList from './MeetingsList.svelte';
  import WasteSchedule from './WasteSchedule.svelte';

  let { section, bundle }: { section: GuideSectionMeta; bundle: GuideBundle } = $props();
</script>

{#if section.type === 'markdown'}
  <!-- Build-time-rendered, link-validated HTML from content/guide/*.md (trusted, not user input). -->
  <div class="md">{@html bundle.content[section.id] ?? ''}</div>
{:else if section.type === 'contacts' && bundle.contacts}
  <ContactsList contacts={bundle.contacts} />
{:else if section.type === 'meetings' && bundle.meetings}
  <MeetingsList meetings={bundle.meetings} />
{:else if section.type === 'waste'}
  <WasteSchedule />
{/if}

<style>
  .md {
    line-height: 1.65;
  }
  .md :global(h2) {
    font-family: var(--font-head, sans-serif);
    color: var(--civic-blue, #2c57a0);
    font-size: 1.2rem;
    margin: 1.4rem 0 0.5rem;
  }
  .md :global(h3) {
    font-family: var(--font-head, sans-serif);
    color: var(--civic-blue, #2c57a0);
    font-size: 1.02rem;
    margin: 1.1rem 0 0.4rem;
  }
  .md :global(a) {
    color: var(--civic-blue-link, #386fc5);
  }
  .md :global(ul) {
    padding-left: 1.2rem;
  }
  .md :global(li) {
    margin: 0.2rem 0;
  }
  .md :global(blockquote) {
    margin: 0.6rem 0;
    padding: 0.4rem 0.9rem;
    border-left: 3px solid var(--civic-green, #4ea735);
    background: var(--civic-green-soft, #d9f1dd);
    border-radius: var(--pub-radius-sm, 8px);
  }
  .md :global(strong) {
    color: var(--pub-ink, #2c2c2c);
  }
  /* Images in guide markdown (![alt](/photo.jpg)) -- keep them responsive so a
     large photo never overflows the content column. */
  .md :global(img) {
    display: block;
    max-width: 100%;
    height: auto;
    margin: 0.8rem 0;
    border-radius: var(--pub-radius-sm, 8px);
  }
</style>
