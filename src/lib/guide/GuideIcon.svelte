<script lang="ts">
  import { ICONS } from './icons';

  // Decorative section icon (the text label carries the meaning), so aria-hidden.
  let { name, size = 18 }: { name: string; size?: number } = $props();
  const svg = $derived(ICONS[name] ?? '');
</script>

{#if svg}
  <svg
    class="gicon"
    viewBox="0 0 24 24"
    width={size}
    height={size}
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >{@html svg}</svg>
{/if}

<style>
  .gicon {
    flex: 0 0 auto;
    vertical-align: -0.15em;
  }
</style>
