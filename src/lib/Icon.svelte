<script lang="ts">
  import { ICONS } from './icons';

  // App-wide inline icon: looks `name` up in the shared registry (icons.ts,
  // which folds in the Resident Guide's icon set) and renders it inside the
  // one 24x24 currentColor stroke wrapper every hand-copied icon in the app
  // used to duplicate. Decorative by default (aria-hidden) -- put any
  // accessible label on the surrounding button/link, not here.
  let {
    name,
    size = 18,
    class: className = '',
    fill = 'none',
    style = '',
  }: {
    name: string;
    size?: number;
    class?: string;
    fill?: string;
    style?: string;
  } = $props();

  const svg = $derived(ICONS[name] ?? '');
</script>

{#if svg}
  <svg
    class={className}
    {style}
    viewBox="0 0 24 24"
    width={size}
    height={size}
    {fill}
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >{@html svg}</svg>
{/if}
