<script lang="ts">
  import type { InfoStat } from './types';
  let { stat }: { stat: InfoStat } = $props();

  const SPARK_W = 88;
  const SPARK_H = 22;

  // Normalise a small series into an SVG polyline string. Flat series sit on the
  // mid-line rather than collapsing to the bottom.
  function sparkPoints(series: { x: string; y: number }[]): string {
    const ys = series.map((p) => p.y);
    const min = Math.min(...ys);
    const max = Math.max(...ys);
    const span = max - min || 1;
    const pad = 2;
    const innerW = SPARK_W - pad * 2;
    const innerH = SPARK_H - pad * 2;
    return series
      .map((p, i) => {
        const x = pad + (series.length === 1 ? innerW / 2 : (i / (series.length - 1)) * innerW);
        const y = pad + innerH - ((p.y - min) / span) * innerH;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }
</script>

<div class="stat">
  <span class="value">{stat.value}</span>
  <span class="label">{stat.label}</span>
  {#if stat.spark && stat.spark.length >= 2}
    <svg
      class="spark"
      viewBox="0 0 {SPARK_W} {SPARK_H}"
      role="img"
      aria-label="{stat.label} trend, {stat.spark[0].x} to {stat.spark[stat.spark.length - 1].x}"
    >
      <polyline points={sparkPoints(stat.spark)} fill="none" stroke="var(--civic-green-deep, #1d7f2b)" stroke-width="1.5" />
    </svg>
  {/if}
  {#if stat.hint}<span class="hint">{stat.hint}</span>{/if}
  {#if stat.benchmarks?.length}
    <span class="bench">
      {#each stat.benchmarks as b, i (b.name)}{i > 0 ? ' · ' : ''}{b.name} {b.value}{/each}
    </span>
  {/if}
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
    color: var(--pub-muted, #5c5c5c);
  }
  .hint {
    font-size: 0.76rem;
    color: var(--pub-muted, #5c5c5c);
  }
  .bench {
    margin-top: 0.25rem;
    padding-top: 0.25rem;
    border-top: 1px dashed var(--pub-border, #e3e3e3);
    font-size: 0.72rem;
    color: var(--pub-muted, #5c5c5c);
    font-variant-numeric: tabular-nums;
  }
  .spark {
    margin-top: 0.3rem;
    width: 88px;
    height: 22px;
    overflow: visible;
  }
</style>
