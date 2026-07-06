<script lang="ts">
  import { onDestroy } from 'svelte';
  import { ui } from './store.svelte';
  import Icon from './Icon.svelte';

  // Keep the input itself instant, but debounce the committed query: each
  // keystroke otherwise re-filters + re-clusters all ~1,146 markers, which janks
  // on mobile. 220 ms settles a pause without feeling laggy.
  let value = $state(ui.query);
  let focused = $state(false);
  let timer: ReturnType<typeof setTimeout> | undefined;

  function onInput() {
    clearTimeout(timer);
    timer = setTimeout(() => (ui.query = value), 220);
  }
  onDestroy(() => clearTimeout(timer));

  // The search only runs at >= 2 characters (see searchIds); hint the user while
  // they're focused but still under that minimum.
  const showHint = $derived(focused && value.trim().length < 2);
</script>

<div class="search">
  <div class="field">
    <Icon name="search" size={18} class="icon" />
    <input
      type="search"
      placeholder="Search by name, category, address&hellip;"
      bind:value
      oninput={onInput}
      onfocus={() => (focused = true)}
      onblur={() => (focused = false)}
      aria-label="Search places"
      aria-describedby={showHint ? 'search-hint' : null}
    />
  </div>
  {#if showHint}
    <p id="search-hint" class="hint">Type at least 2 letters to search.</p>
  {/if}
</div>

<style>
  .search {
    padding: 0.75rem 0.9rem 0;
  }
  .field {
    position: relative;
  }
  /* Icon.svelte renders the actual <svg> inside its own component, past this
     component's style scope -- :global() reaches through to it (same idiom as
     Guide.svelte's `.sectionnav button :global(.gicon)`). */
  .field :global(.icon) {
    position: absolute;
    left: 0.65rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--pub-muted, #5c5c5c);
    pointer-events: none;
  }
  input {
    width: 100%;
    box-sizing: border-box;
    padding: 0.55rem 0.7rem 0.55rem 2.1rem;
    font-family: var(--font-body);
    font-size: 0.95rem;
    border: 1px solid #adb5bd;
    border-radius: var(--pub-radius);
    transition:
      border-color var(--motion-duration),
      background var(--motion-duration);
  }
  input:focus {
    outline: none;
    border-color: var(--civic-green);
    background: var(--civic-green-soft);
  }
  .hint {
    margin: 0.3rem 0 0;
    font-size: 0.78rem;
    color: var(--pub-muted, #5c5c5c);
  }
</style>
