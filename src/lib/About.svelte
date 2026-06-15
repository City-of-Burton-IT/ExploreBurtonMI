<script lang="ts">
  import type { AppConfig } from './types';
  import { ui, openAbout, closeAbout } from './store.svelte';
  import { reportOutdatedMailto } from './feedback';

  // `showButton` renders the inline "About" trigger. When false, only the dialog
  // is mounted (opened from elsewhere, e.g. the map © button or the Guide).
  let { config, showButton = true }: { config: AppConfig; showButton?: boolean } = $props();

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') closeAbout();
  }
</script>

<svelte:window onkeydown={onKeydown} />

{#if showButton}
  <button class="about-btn" onclick={openAbout}>About</button>
{/if}

{#if ui.aboutOpen}
  <div
    class="backdrop"
    role="presentation"
    onclick={closeAbout}
  >
    <div class="modal" role="dialog" aria-modal="true" aria-label="About this map">
      <button class="close" onclick={closeAbout} aria-label="Close">&times;</button>
      <h2>About {config.project.name}</h2>
      <p>{config.project.tagline}</p>
      <p class="note">
        Listings combine OpenStreetMap and Overture Maps business data with curated
        City of Burton facility records; government facility locations have been
        verified against the City's published addresses.
      </p>
      <hr />
      <p class="attrib">
        Built on the open-source
        <a href="https://github.com/codeforboston/finda" target="_blank" rel="noopener noreferrer">Finda</a>
        concept by Code for Boston (MIT License). Imagery &copy;
        <a href="https://www.michigan.gov" target="_blank" rel="noopener noreferrer">State of Michigan</a>;
        map reference &copy; <a href="https://www.esri.com" target="_blank" rel="noopener noreferrer">Esri</a>;
        place data &copy;
        <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>
        contributors &amp;
        <a href="https://overturemaps.org" target="_blank" rel="noopener noreferrer">Overture Maps Foundation</a>.
        Resident Guide icons by <a href="https://lucide.dev" target="_blank" rel="noopener noreferrer">Lucide</a> (ISC).
      </p>
      <p class="privacy">
        <!-- Absolute URL so the link resolves from inside the bundled mobile app,
             not just on the web origin. -->
        <a href="https://explore.burtonmi.gov/privacy.html" target="_blank" rel="noopener noreferrer">Privacy policy</a>
      </p>
      <p class="feedback">
        See something out of date? <a href={reportOutdatedMailto()}>Report outdated information</a>.
      </p>
    </div>
  </div>
{/if}

<style>
  .about-btn {
    border: none;
    background: var(--civic-accent-bg);
    color: #fff;
    border-radius: var(--pub-radius);
    padding: 0.4rem 0.95rem;
    cursor: pointer;
    font-family: var(--font-body);
    font-weight: 700;
    font-size: 0.9rem;
    transition: background var(--motion-duration);
  }
  .about-btn:hover {
    background: var(--civic-accent-bg-hover);
  }
  .about-btn:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }

  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    display: grid;
    place-items: center;
    z-index: 2000;
    padding: 1rem;
  }
  .modal {
    position: relative;
    background: var(--pub-surface);
    color: var(--pub-ink);
    border-radius: var(--pub-radius-lg);
    max-width: 480px;
    width: 100%;
    padding: 1.6rem 1.7rem;
    box-shadow: 0 1rem 3rem rgba(0, 0, 0, 0.175);
    line-height: 1.6;
  }
  .close {
    position: absolute;
    top: 0.5rem;
    right: 0.7rem;
    border: none;
    background: none;
    font-size: 1.6rem;
    line-height: 1;
    cursor: pointer;
    color: var(--pub-muted);
  }
  .close:hover {
    color: var(--civic-blue);
  }
  h2 {
    margin: 0 1.5rem 0.6rem 0;
    font-family: var(--font-head);
    font-weight: 700;
    color: var(--civic-blue);
  }
  .note {
    background: var(--civic-green-soft);
    border-left: 3px solid var(--civic-green);
    border-radius: var(--pub-radius-sm);
    padding: 0.7rem 0.85rem;
    font-size: 0.9rem;
  }
  hr {
    border: none;
    border-top: 2px dashed var(--civic-green);
    margin: 1.1rem 0;
  }
  .attrib {
    font-size: 0.82rem;
    color: var(--pub-muted);
  }
  .privacy {
    margin: 0.6rem 0 0;
    font-size: 0.85rem;
    font-weight: 600;
  }
  .feedback {
    margin: 0.4rem 0 0;
    font-size: 0.82rem;
    color: var(--pub-muted);
  }
  a {
    color: var(--civic-blue-link);
  }
</style>
