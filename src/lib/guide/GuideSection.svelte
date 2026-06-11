<script lang="ts">
  import type { GuideBundle, GuideSectionMeta } from '../types';
  import { reveal } from '../actions/reveal';
  import { lightboxImages } from '../actions/lightboxImages';
  import ContactsList from './ContactsList.svelte';
  import MeetingsList from './MeetingsList.svelte';
  import WasteSchedule from './WasteSchedule.svelte';
  import CivicClerkMeetings from './CivicClerkMeetings.svelte';
  import VideoEmbed from './VideoEmbed.svelte';

  let {
    section,
    bundle,
    openImage,
  }: {
    section: GuideSectionMeta;
    bundle: GuideBundle;
    openImage: (src: string, caption: string) => void;
  } = $props();
</script>

{#if section.type === 'markdown'}
  <!-- Build-time-rendered, link-validated HTML from content/guide/*.md (trusted, not user input). -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="md" use:reveal use:lightboxImages={openImage}>{@html bundle.content[section.id] ?? ''}</div>
{:else if section.type === 'contacts' && bundle.contacts}
  <ContactsList contacts={bundle.contacts} />
{:else if section.type === 'meetings' && bundle.meetings}
  <MeetingsList meetings={bundle.meetings} />
{:else if section.type === 'waste'}
  <WasteSchedule />
{:else if section.type === 'civicclerk'}
  <CivicClerkMeetings />
{:else if section.type === 'video' && section.src}
  <VideoEmbed src={section.src} title={section.title} provider={section.provider ?? ''} />
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
  /* Images in guide markdown (![alt](/photo.jpg)) -- responsive, and click-to-zoom
     via the lightboxImages action (zoom-in cursor + focus ring added there). */
  .md :global(img) {
    display: block;
    max-width: 100%;
    height: auto;
    margin: 0.8rem 0;
    border-radius: var(--pub-radius-sm, 8px);
  }
  .md :global(img:focus-visible) {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }

  /* Typed callout boxes (::: containers in the markdown). */
  .md :global(.callout) {
    display: flex;
    gap: 0.7rem;
    margin: 1rem 0;
    padding: 0.8rem 1rem;
    border-radius: var(--pub-radius-sm, 8px);
    border-left: 4px solid var(--c, var(--civic-blue, #2c57a0));
    background: var(--cbg, #eef3fb);
  }
  .md :global(.callout-icon) {
    width: 1.3rem;
    height: 1.3rem;
    flex: 0 0 auto;
    margin-top: 0.1rem;
    color: var(--c, var(--civic-blue, #2c57a0));
  }
  .md :global(.callout-body) {
    min-width: 0;
  }
  .md :global(.callout-body > :first-child) {
    margin-top: 0;
  }
  .md :global(.callout-body > :last-child) {
    margin-bottom: 0;
  }
  .md :global(.callout-title) {
    margin: 0 0 0.25rem;
    font-family: var(--font-head, sans-serif);
    font-weight: 700;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--c, var(--civic-blue, #2c57a0));
  }
  .md :global(.callout--tip) {
    --c: var(--civic-green-deep, #1d7f2b);
    --cbg: var(--civic-green-soft, #d9f1dd);
  }
  .md :global(.callout--important) {
    --c: #b26a00;
    --cbg: #fff6e6;
  }
  .md :global(.callout--key-date) {
    --c: var(--civic-blue, #2c57a0);
    --cbg: var(--civic-blue-soft, #d7e1f3);
  }
  .md :global(.callout--contact) {
    --c: var(--civic-blue-deep, #1e437e);
    --cbg: #eef3fb;
  }
</style>
