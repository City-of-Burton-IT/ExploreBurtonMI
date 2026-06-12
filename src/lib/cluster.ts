// Helpers for the map cluster preview (hover tooltip + tap popup): turn the names
// of the places inside a cluster bubble into a short, de-duplicated, sorted list
// with an "+N more" overflow count. Pure so it's unit-tested; the Leaflet wiring
// lives in Map.svelte.

/** The most child places a cluster can hold and still show the tap-preview popup
 *  (rather than zooming to drill down). */
export const CLUSTER_PREVIEW_MAX = 12;

/** A de-duplicated, alphabetically-sorted name list capped at `max`, plus the
 *  number of additional names not shown. */
export function clusterSummary(
  names: string[],
  max = 6,
): { shown: string[]; more: number } {
  const unique = [...new Set(names.map((n) => n.trim()).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b),
  );
  return { shown: unique.slice(0, max), more: Math.max(0, unique.length - max) };
}
