<script lang="ts">
  import { trendLayout, formatValue } from './scale';

  let {
    points,
    unit = '',
  }: { points: { x: string; y: number }[]; unit?: string } = $props();

  const W = 320;
  const H = 150;
  const PAD = 28;

  const layout = $derived(trendLayout(points, W, H, PAD));
  const color = '#2c57a0'; // civic blue
</script>

{#if layout.dots.length === 0}
  <p class="nodata">No data available.</p>
{:else}
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Trend over time" class="trend">
    <!-- baseline -->
    <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} class="axis" />
    {#if layout.dots.length > 1}
      <polyline points={layout.polyline} fill="none" stroke={color} stroke-width="2.5" />
    {/if}
    {#each layout.dots as d (d.label)}
      <circle cx={d.x} cy={d.y} r="3.5" fill={color}>
        <title>{d.label}: {formatValue(d.value, unit)}</title>
      </circle>
      <text x={d.x} y={H - PAD + 16} class="xlabel">{d.label}</text>
      <text x={d.x} y={d.y - 8} class="vlabel">{formatValue(d.value, unit)}</text>
    {/each}
  </svg>
{/if}

<style>
  .trend {
    width: 100%;
    max-width: 420px;
    height: auto;
  }
  .axis {
    stroke: #d8dde4;
    stroke-width: 1;
  }
  .xlabel {
    font-size: 10px;
    fill: #666;
    text-anchor: middle;
    font-family: var(--font-body, sans-serif);
  }
  .vlabel {
    font-size: 10px;
    fill: #333;
    text-anchor: middle;
    font-weight: 600;
    font-family: var(--font-body, sans-serif);
  }
  .nodata {
    color: #888;
    font-size: 0.9rem;
    font-style: italic;
  }
</style>
