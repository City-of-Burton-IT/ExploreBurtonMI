<script lang="ts">
  import Icon from '../Icon.svelte';

  // Decorative section icon (the text label carries the meaning), so aria-hidden
  // (handled by Icon.svelte). Delegates to the app-wide Icon component -- this
  // wrapper just keeps the guide's own default size and vertical-align tweak.
  let { name, size = 18 }: { name: string; size?: number } = $props();
</script>

<Icon {name} {size} class="gicon" />

<style>
  /* Icon.svelte renders the <svg> in its own component scope; :global() reaches
     through to it (same idiom as Guide.svelte's `.sectionnav button :global(.gicon)`). */
  :global(.gicon) {
    flex: 0 0 auto;
    vertical-align: -0.15em;
  }
</style>
