<script lang="ts">
  import type { GuideSectionMeta } from '../types';
  import { safeHref } from '../templates';
  import GuideIcon from './GuideIcon.svelte';

  let {
    sections,
    activeId,
    pdf,
    onSelect,
    onAbout,
  }: {
    sections: GuideSectionMeta[];
    activeId: string;
    pdf?: string;
    onSelect: (id: string) => void;
    onAbout: () => void;
  } = $props();

  let nav: HTMLElement;

  $effect(() => {
    const id = activeId;
    if (typeof window === 'undefined' || !nav) return;
    queueMicrotask(() => {
      const button = nav.querySelector<HTMLButtonElement>(`button[data-guide-section="${id}"]`);
      if (!button) return;
      const focused = document.activeElement;
      if (focused instanceof HTMLElement && nav.contains(focused) && focused.dataset.guideSection) {
        button.focus({ preventScroll: true });
      }
      if (window.matchMedia('(max-width: 860px)').matches) {
        const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        button.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'nearest', inline: 'nearest' });
      }
    });
  });
</script>

<nav bind:this={nav} class="sectionnav" aria-label="Resident Guide sections">
  <ul>
    {#each sections as section (section.id)}
      <li>
        <button
          type="button"
          data-guide-section={section.id}
          class:active={section.id === activeId}
          aria-current={section.id === activeId ? 'page' : undefined}
          onclick={() => onSelect(section.id)}
        >
          {#if section.icon}<GuideIcon name={section.icon} />{/if}
          <span class="sec-label">{section.title}</span>
        </button>
      </li>
    {/each}
  </ul>
  <button class="about" type="button" onclick={onAbout}>About this site &amp; credits</button>
  {#if pdf}
    <a class="pdf" href={safeHref(pdf)} target="_blank" rel="noopener noreferrer">
      Download the official packet (PDF)
    </a>
  {/if}
</nav>

<style>
  .sectionnav {
    flex: 0 0 240px;
    border-right: 1px solid var(--pub-border, #e3e3e3);
    overflow-y: auto;
    padding: 0.8rem 0.6rem;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  ul {
    list-style: none;
    margin: 0 0 0.6rem;
    padding: 0;
  }
  button {
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
  button :global(.gicon) {
    color: var(--civic-blue, #2c57a0);
  }
  .sec-label {
    min-width: 0;
  }
  button:hover {
    background: var(--pub-surface-2);
  }
  button.active {
    background: var(--civic-blue-soft, #d7e1f3);
    color: var(--civic-blue-deep, #1e437e);
    font-weight: 700;
    box-shadow: inset 3px 0 0 var(--civic-blue, #2c57a0);
  }
  .about,
  .pdf {
    font-size: 0.85rem;
    color: var(--civic-blue-link, #386fc5);
    padding: 0.5rem 0.7rem;
  }
  .about {
    margin-top: auto;
  }
  .pdf {
    margin-top: 0;
  }
  .about:hover {
    text-decoration: underline;
  }
  .about:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }

  @media (max-width: 860px) {
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
    ul {
      display: flex;
      gap: 0.4rem;
      margin: 0;
    }
    button {
      white-space: nowrap;
      width: auto;
      min-height: 48px;
    }
    button.active {
      box-shadow: none;
    }
    .about,
    .pdf {
      margin-top: 0;
      white-space: nowrap;
    }
  }
</style>
