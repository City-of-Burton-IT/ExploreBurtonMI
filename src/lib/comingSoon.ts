import { Capacitor } from '@capacitor/core';

// COMING-SOON GATE (soft launch)
// ==============================
// While ENABLED, public web visitors see a holding page instead of the site.
// The NATIVE app is NEVER gated -- it skips this entirely and keeps pulling live
// data (see remote.ts), so you can keep viewing production in the Android app.
// The bypass is a typed phrase saved in localStorage, so you unlock a device once
// and stay unlocked. You can also share a bypass link: ?unlock=<phrase>.
//
// This is a SOFT gate: it re-hides the front door for a soft launch. It is NOT
// access control -- the app bundle and the open-data JSON files are still public,
// and anyone determined can read the phrase out of the shipped JavaScript. It
// deters the public and the soft launch; it does not secure the content.
//
// AT LAUNCH: set COMING_SOON_ENABLED = false and redeploy to open the site fully.
// Internal-preview builds (VITE_INTERNAL_PREVIEW=1 at build time) disable the
// gate so staff mirrors show the site directly; the public build is unaffected.
export const COMING_SOON_ENABLED = import.meta.env.VITE_INTERNAL_PREVIEW === '1' ? false : true;

// The phrase you type on the holding page (or pass as ?unlock=...) to reveal the
// site. CHANGE THIS to whatever you like. Matching is case-insensitive + trimmed.
const UNLOCK_PHRASE = 'burton-preview';

// localStorage key remembering that this device has unlocked.
const STORAGE_KEY = 'eb-unlocked';

const isNative = Capacitor.isNativePlatform();

const normalize = (s: string): string => s.trim().toLowerCase();

/** True if this device has already entered the correct phrase. */
export function isUnlocked(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

/** Persist the unlocked state for this device (no-op if storage is unavailable). */
function setUnlocked(): void {
  try {
    localStorage.setItem(STORAGE_KEY, '1');
  } catch {
    /* private mode / storage disabled -> stays gated, no crash */
  }
}

/** Check a typed phrase; on a match, persist the unlock and return true. */
export function tryUnlock(input: string): boolean {
  if (normalize(input) === normalize(UNLOCK_PHRASE)) {
    setUnlocked();
    return true;
  }
  return false;
}

/**
 * Should the holding page be shown instead of the app?
 *   - Native app: never (returns false).
 *   - Web: only when the gate is enabled AND this device hasn't unlocked.
 * Also honors a ?unlock=<phrase> query param so a bypass link unlocks on arrival.
 */
export function shouldGate(): boolean {
  if (!COMING_SOON_ENABLED || isNative) return false;
  try {
    const param = new URLSearchParams(window.location.search).get('unlock');
    if (param && tryUnlock(param)) return false;
  } catch {
    /* malformed URL -> ignore, fall through to the stored state */
  }
  return !isUnlocked();
}
