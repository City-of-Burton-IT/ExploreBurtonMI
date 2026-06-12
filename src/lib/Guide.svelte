<script lang="ts">
  import { onMount } from 'svelte';
  import type { GuideBundle } from './types';
  import { ui, setGuideSection, openAbout } from './store.svelte';
  import { safeHref } from './templates';
  import { dataFetch } from './remote';
  import GuideSection from './guide/GuideSection.svelte';
  import GuideIcon from './guide/GuideIcon.svelte';
  import Lightbox from './Lightbox.svelte';
  import OfflineBadge from './OfflineBadge.svelte';

  let bundle = $state<GuideBundle | null>(null);
  let loading = $state(true);
  let lightbox = $state<{ show: (src: string, caption: string) => void }>();
  const openImage = (src: string, caption: string) => lightbox?.show(src, caption);

  onMount(async () => {
    try {
      const r = await dataFetch('guide.json');
      if (r.ok) bundle = (await r.json()) as GuideBundle;
    } catch {
      bundle = null;
    }
    loading = false;
  });

  const activeId = $derived(ui.guideSection ?? bundle?.sections[0]?.id ?? null);
  const activeSection = $derived(bundle?.sections.find((s) => s.id === activeId) ?? null);

  // Sections whose widget renders its own (more specific) offline badge -- skip the
  // generic guide-level one there so it isn't doubled when offline.
  const SELF_BADGED = new Set(['waste', 'civicclerk']);
</script>

<section class="guide" aria-label="Resident Guide">
  {#if loading}
    <p class="state">Loading&hellip;</p>
  {:else if !bundle}
    <p class="state">The resident guide is temporarily unavailable. Please check back soon.</p>
  {:else}
    <nav class="sectionnav" aria-label="Guide sections">
      <ul>
        {#each bundle.sections as s (s.id)}
          <li>
            <button class:active={s.id === activeId} onclick={() => setGuideSection(s.id)}>
              {#if s.icon}<GuideIcon name={s.icon} />{/if}
              <span class="sec-label">{s.title}</span>
            </button>
          </li>
        {/each}
      </ul>
      <button class="about" onclick={openAbout}>About this site &amp; credits</button>
      {#if bundle.pdf}
        <a class="pdf" href={safeHref(bundle.pdf)} target="_blank" rel="noopener noreferrer">
          Download the official packet (PDF)
        </a>
      {/if}
    </nav>

    <div class="guide-body">
      {#if !SELF_BADGED.has(activeSection?.type ?? '')}
        <OfflineBadge />
      {/if}
      {#if activeSection}
        <h2>
          {#if activeSection.icon}<GuideIcon name={activeSection.icon} size={24} />{/if}
          {activeSection.title}
        </h2>
        <GuideSection section={activeSection} {bundle} {openImage} />
      {/if}
    </div>
  {/if}
  <Lightbox bind:this={lightbox} />
</section>

<style>
  .guide {
    height: 100%;
    display: flex;
    min-height: 0;
    background: #fff;
  }
  .state {
    padding: 2rem;
    color: var(--pub-muted, #5c5c5c);
  }
  .sectionnav {
    flex: 0 0 240px;
    border-right: 1px solid var(--pub-border, #e3e3e3);
    overflow-y: auto;
    padding: 0.8rem 0.6rem;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .sectionnav ul {
    list-style: none;
    margin: 0 0 0.6rem;
    padding: 0;
  }
  .sectionnav button {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.55rem;
    text-align: left;
    border: none;
    background: none;
    border-radius: var(--pub-radius-sm, 8px);
    padding: 0.5rem 0.7rem;
    font-family: var(--font-body, sans-serif);
    font-size: 0.92rem;
    color: var(--pub-ink, #2c2c2c);
    cursor: pointer;
  }
  .sectionnav button :global(.gicon) {
    color: var(--civic-blue, #2c57a0);
  }
  .sec-label {
    min-width: 0;
  }
  .sectionnav button:hover {
    background: #f5f7fa;
  }
  .sectionnav button.active {
    background: var(--civic-blue-soft, #d7e1f3);
    color: var(--civic-blue-deep, #1e437e);
    font-weight: 700;
    box-shadow: inset 3px 0 0 var(--civic-blue, #2c57a0);
  }
  /* "About" anchors the guide's footer actions to the bottom of the nav column;
     the PDF download sits directly beneath it as the very last item. */
  .pdf {
    margin-top: 0;
    font-size: 0.85rem;
    color: var(--civic-blue-link, #386fc5);
    padding: 0.5rem 0.7rem;
  }
  .about {
    margin-top: auto;
    border: none;
    background: none;
    text-align: left;
    padding: 0.5rem 0.7rem;
    font-family: var(--font-body, sans-serif);
    font-size: 0.85rem;
    color: var(--civic-blue-link, #386fc5);
    cursor: pointer;
  }
  .about:hover {
    text-decoration: underline;
  }
  .about:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: var(--pub-radius-sm, 8px);
  }
  .guide-body {
    flex: 1 1 auto;
    overflow-y: auto;
    padding: 1.4rem 1.8rem 2.4rem;
    min-width: 0;
  }
  .guide-body h2 {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    margin: 0 0 0.8rem;
    font-family: var(--font-head, sans-serif);
    font-weight: 700;
    font-size: 1.5rem;
    color: var(--civic-blue, #2c57a0);
  }

  /* Phones/tablets: section list becomes a horizontal scroller above the content. */
  @media (max-width: 860px) {
    .guide {
      flex-direction: column;
    }
    .sectionnav {
      flex: 0 0 auto;
      flex-direction: row;
      align-items: center;
      gap: 0.4rem;
      border-right: none;
      border-bottom: 1px solid var(--pub-border, #e3e3e3);
      overflow-x: auto;
      overflow-y: hidden;
      padding: 0.5rem 0.7rem;
    }
    .sectionnav ul {
      display: flex;
      gap: 0.4rem;
      margin: 0;
    }
    .sectionnav button {
      white-space: nowrap;
      width: auto;
      /* WCAG 2.5.8: comfortable touch target on phones. */
      min-height: 48px;
    }
    .sectionnav button.active {
      box-shadow: none;
    }
    .pdf {
      margin-top: 0;
      white-space: nowrap;
    }
    .about {
      margin-top: 0;
      white-space: nowrap;
    }
  }
</style>
