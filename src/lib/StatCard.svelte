<script lang="ts">
  import type { InfoStat } from './types';
  let { stat }: { stat: InfoStat } = $props();
</script>

<div class="stat">
  <span class="value">{stat.value}</span>
  <span class="label">{stat.label}</span>
  {#if stat.hint}<span class="hint">{stat.hint}</span>{/if}
</div>

<style>
  .stat {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    background: #fff;
    border: 1px solid #e5e9ee;
    border-radius: var(--pub-radius, 10px);
    padding: 0.9rem 1rem;
  }
  .value {
    font-family: var(--font-head, sans-serif);
    font-weight: 700;
    font-size: 1.6rem;
    line-height: 1.1;
    color: var(--civic-blue, #2c57a0);
  }
  .label {
    font-size: 0.74rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #777;
  }
  .hint {
    font-size: 0.76rem;
    color: #999;
  }
</style>
