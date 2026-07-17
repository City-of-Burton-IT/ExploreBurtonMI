<script lang="ts">
  import type { GuideBundle } from './types';
  import { ui, setGuideSection, openAbout } from './store.svelte';
  import { loadJson } from './loadJson.svelte';
  import { validateGuideBundle } from './guide/guideBundle';
  import GuideNav from './guide/GuideNav.svelte';
  import GuideSection from './guide/GuideSection.svelte';
  import GuideIcon from './guide/GuideIcon.svelte';
  import Lightbox from './Lightbox.svelte';
  import OfflineBadge from './OfflineBadge.svelte';

  const guide = loadJson<GuideBundle | null>('guide.json', validateGuideBundle, null);
  const bundle = $derived(guide.data);
  const loading = $derived(guide.loading);
  let lightbox = $state<{ show: (src: string, caption: string) => void }>();
  const openImage = (src: string, caption: string) => lightbox?.show(src, caption);

  const activeId = $derived(ui.guideSection ?? bundle?.sections[0]?.id ?? '');
  const activeSection = $derived(bundle?.sections.find((section) => section.id === activeId) ?? null);
  const SELF_BADGED = new Set(['waste', 'civicclerk']);
</script>

<section class="guide" aria-label="Resident Guide">
  {#if loading}
    <p class="state">Loading&hellip;</p>
  {:else if !bundle}
    <p class="state">The resident guide is temporarily unavailable. Please check back soon.</p>
  {:else}
    <GuideNav
      sections={bundle.sections}
      {activeId}
      pdf={bundle.pdf}
      onSelect={setGuideSection}
      onAbout={openAbout}
    />
    <div class="guide-body">
      {#if !SELF_BADGED.has(activeSection?.type ?? '')}<OfflineBadge />{/if}
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
    background: var(--pub-surface);
  }
  .state {
    padding: 2rem;
    color: var(--pub-muted, #5c5c5c);
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
  @media (max-width: 860px) {
    .guide {
      flex-direction: column;
    }
  }
</style>
