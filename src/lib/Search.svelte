<script lang="ts">
  import { ui } from './store.svelte';
</script>

<div class="search">
  <input
    type="search"
    placeholder="Search by name, category, address&hellip;"
    bind:value={ui.query}
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
