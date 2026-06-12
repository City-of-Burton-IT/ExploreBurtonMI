// Saved / favorite places (#62). Per-device only -- no accounts. The set of saved
// place ids persists in localStorage as a JSON array. Pure helpers here so the
// load/serialize/toggle logic is unit-tested; the store owns the reactive state
// and the actual localStorage read/write.

export const SAVED_KEY = 'eb-saved-places';

/** Parse the stored saved-ids value into a Set. A missing/corrupt/non-array
 *  value yields an empty set (never throws). */
export function loadSaved(raw: string | null): Set<string> {
  if (!raw) return new Set();
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((x): x is string => typeof x === 'string'));
  } catch {
    return new Set();
  }
}

/** Serialize the saved-ids set for localStorage (stable array form). */
export function serializeSaved(ids: Set<string>): string {
  return JSON.stringify([...ids]);
}

/** Return a NEW set with `id` toggled (Svelte reactivity needs a fresh reference). */
export function toggleSaved(ids: Set<string>, id: string): Set<string> {
  const next = new Set(ids);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  return next;
}
