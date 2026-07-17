<script lang="ts">
  import type { GuideBundle } from './types';
  import { ui, setGuideSection, openAbout } from './store.svelte';
  import { loadJson } from './loadJson.svelte';
  import { validateGuideBundle } from './guide/guideBundle';
  import GuideNav from './guide/GuideNav.svelte';
  import GuideContent from './guide/GuideContent.svelte';
  import Lightbox from './Lightbox.svelte';

  const guide = loadJson<GuideBundle | null>('guide.json', validateGuideBundle, null);
  const bundle = $derived(guide.data);
  const loading = $derived(guide.loading);
  let lightbox = $state<{ show: (src: string, caption: string) => void }>();
  const openImage = (src: string, caption: string) => lightbox?.show(src, caption);

  const activeId = $derived(ui.guideSection ?? bundle?.sections[0]?.id ?? '');
  const activeSection = $derived(bundle?.sections.find((section) => section.id === activeId) ?? null);
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
    {#if activeSection}<GuideContent section={activeSection} {bundle} {openImage} />{/if}
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
  @media (max-width: 860px) {
    .guide {
      flex-direction: column;
    }
  }
</style>
