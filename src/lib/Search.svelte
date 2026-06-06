<script lang="ts">
  import { onDestroy } from 'svelte';
  import { ui } from './store.svelte';

  // Keep the input itself instant, but debounce the committed query: each
  // keystroke otherwise re-filters + re-clusters all ~1,146 markers, which janks
  // on mobile. 220 ms settles a pause without feeling laggy.
  let value = $state(ui.query);
  let timer: ReturnType<typeof setTimeout> | undefined;

  function onInput() {
    clearTimeout(timer);
    timer = setTimeout(() => (ui.query = value), 220);
  }
  onDestroy(() => clearTimeout(timer));
</script>

<div class="search">
  <input
    type="search"
    placeholder="Search by name, category, address&hellip;"
    bind:value
    oninput={onInput}
    aria-label="Search places"
  />
</div>

<style>
  .search {
    padding: 0.75rem 0.9rem 0;
  }
  input {
    width: 100%;
    padding: 0.55rem 0.7rem;
    font-family: var(--font-body);
    font-size: 0.95rem;
    border: 1px solid #adb5bd;
    border-radius: var(--pub-radius);
    transition: border-color 0.15s, background 0.15s;
  }
  input:focus {
    outline: none;
    border-color: var(--civic-green);
    background: var(--civic-green-soft);
  }
</style>
