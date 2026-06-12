// Theme preference (#61). A toggle, not a forced media query: dark applies only
// when the resident opts in, so shipping it can't regress dark-OS users who never
// chose it. Persisted per-device in localStorage; applied as data-theme on <html>.
// Pure helpers here (testable); the store owns the DOM + matchMedia wiring.

export type ThemePref = 'system' | 'light' | 'dark';
export type Theme = 'light' | 'dark';

export const THEME_KEY = 'eb-theme';
export const THEME_PREFS: ThemePref[] = ['system', 'light', 'dark'];

/** Parse the stored preference. Unknown/missing -> 'light' (safe default: dark is
 *  opt-in, never forced on first load). Flip to 'system' once the dark palette is
 *  verified if you want dark-OS users to get it automatically. */
export function loadThemePref(raw: string | null): ThemePref {
  return raw === 'light' || raw === 'dark' || raw === 'system' ? raw : 'light';
}

/** Resolve a preference to the concrete theme to apply, given the OS setting. */
export function resolveTheme(pref: ThemePref, systemPrefersDark: boolean): Theme {
  if (pref === 'system') return systemPrefersDark ? 'dark' : 'light';
  return pref;
}
