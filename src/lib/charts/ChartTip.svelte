<script lang="ts">
  // Small floating tooltip shared by the interactive charts. Positioned in the
  // coordinate space of a `position: relative` chart host (x/y are offsets within
  // it). Non-interactive so it never eats pointer events.
  let {
    x = 0,
    y = 0,
    show = false,
    label = '',
    value = '',
    pct = null,
  }: {
    x?: number;
    y?: number;
    show?: boolean;
    label?: string;
    value?: string;
    pct?: number | null;
  } = $props();
</script>

{#if show}
  <div class="charttip" style:left="{x}px" style:top="{y}px" role="status" aria-live="polite">
    <span class="t-label">{label}</span>
    <span class="t-val">{value}{#if pct != null} &middot; {pct}%{/if}</span>
  </div>
{/if}

<style>
  .charttip {
    position: absolute;
    transform: translate(-50%, calc(-100% - 10px));
    pointer-events: none;
    background: #1f2a37;
    color: #fff;
    padding: 0.32rem 0.55rem;
    border-radius: 6px;
    font-size: 0.78rem;
    line-height: 1.3;
    white-space: nowrap;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.28);
    z-index: 5;
    display: flex;
    flex-direction: column;
    max-width: 220px;
  }
  .t-label {
    font-weight: 700;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .t-val {
    opacity: 0.9;
  }
</style>
