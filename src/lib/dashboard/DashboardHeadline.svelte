<script lang="ts">
  let { headline }: { headline: string } = $props();
</script>

<p class="headline">{headline}</p>

<style>
  .headline {
    margin: 0 0 1rem;
    max-width: 72ch;
    color: var(--pub-ink);
    font-family: var(--font-head, sans-serif);
    font-size: clamp(1.08rem, 2.2vw, 1.3rem);
    font-weight: 600;
    line-height: 1.4;
  }
</style>
