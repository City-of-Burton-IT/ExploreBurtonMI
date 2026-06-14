// Push notifications (#64) -- CLIENT SCAFFOLD, inert until Firebase is wired.
//
// Decisions (2026-06-12): opt-in only; topic-based (NO per-device token leaves
// the app, no per-resident record); topics = alerts / service / meetings;
// Android-first. Send path + approval gate live server-side (Power Automate ->
// FCM HTTP v1), see the spec.
//
// "Inert until Firebase later" -- per the build decision, this ships now but does
// nothing real until these LATER steps are done (documented in the spec):
//   1. create the Firebase project, add android/app/google-services.json
//   2. npm i @capacitor-firebase/messaging firebase
//   3. npx cap sync android  (registers the native plugin)
// Until then the dynamic import below resolves to null and every call no-ops, so
// the web build, the web bundle, and the current APK are all unaffected. The
// plugin module name is held in a variable so the bundler does NOT try to resolve
// or bundle it before it exists (type-erased on purpose).

import { Capacitor } from '@capacitor/core';

export interface PushTopic {
  id: string;
  label: string;
  description: string;
}

// The three category topics a resident can opt into. Subscribing to a topic is
// anonymous group membership -- no token, no PII.
export const PUSH_TOPICS: PushTopic[] = [
  { id: 'alerts', label: 'Emergency alerts', description: 'Public-safety and emergency notices.' },
  { id: 'service', label: 'Service disruptions', description: 'Water main breaks, road closures, outages.' },
  { id: 'meetings', label: 'Meeting reminders', description: 'Upcoming city council meetings.' },
];

const TOPIC_IDS = new Set(PUSH_TOPICS.map((t) => t.id));
export const PUSH_PREFS_KEY = 'eb-push-topics';

/** Push is only meaningful in the native app. */
export function isPushSupported(): boolean {
  return Capacitor.isNativePlatform();
}

/** True only when push is BOTH supported (native) AND actually wired (the
 *  messaging plugin is installed = Firebase is configured). The settings UI
 *  gates on this so residents never see toggles that don't do anything yet. */
export async function isPushAvailable(): Promise<boolean> {
  return (await loadMessaging()) !== null;
}

/** Parse the stored opt-in set (a JSON array of topic ids), dropping anything
 *  not in the current topic list. Returns a Set; never throws. */
export function parsePrefs(raw: string | null): Set<string> {
  if (!raw) return new Set();
  try {
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return new Set();
    return new Set(arr.filter((id) => typeof id === 'string' && TOPIC_IDS.has(id)));
  } catch {
    return new Set();
  }
}

/** Serialize an opt-in set to storage form (sorted for stable output). */
export function serializePrefs(prefs: Set<string>): string {
  return JSON.stringify([...prefs].filter((id) => TOPIC_IDS.has(id)).sort());
}

export function loadPrefs(): Set<string> {
  try {
    return parsePrefs(localStorage.getItem(PUSH_PREFS_KEY));
  } catch {
    return new Set();
  }
}

function savePrefs(prefs: Set<string>): void {
  try {
    localStorage.setItem(PUSH_PREFS_KEY, serializePrefs(prefs));
  } catch {
    /* private mode -- the OS subscription still holds for the session */
  }
}

// Minimal shape of the bits of @capacitor-firebase/messaging we call. Kept local
// so the app compiles before the plugin is installed (type-erased import).
interface FirebaseMessagingLike {
  requestPermissions(): Promise<{ receive: string }>;
  subscribeToTopic(opts: { topic: string }): Promise<void>;
  unsubscribeFromTopic(opts: { topic: string }): Promise<void>;
}

/** Load the messaging plugin at runtime, or null if it isn't installed yet
 *  (the "Firebase later" state) or we're on the web. The module name is a
 *  variable so the bundler leaves it as a runtime import. */
async function loadMessaging(): Promise<FirebaseMessagingLike | null> {
  if (!isPushSupported()) return null;
  const moduleName = '@capacitor-firebase/messaging';
  try {
    const mod = await import(/* @vite-ignore */ moduleName);
    return (mod.FirebaseMessaging ?? null) as FirebaseMessagingLike | null;
  } catch {
    return null; // plugin not installed yet -> inert
  }
}

export interface PushEnableResult {
  ok: boolean;
  /** true when the OS notification permission was granted */
  granted: boolean;
  /** false when push isn't available yet (web, or Firebase not wired) */
  available: boolean;
}

/** Request the OS notification permission once, so the per-topic toggles can act.
 *  No-ops (available:false) until the plugin is installed. */
export async function ensurePermission(): Promise<PushEnableResult> {
  const messaging = await loadMessaging();
  if (!messaging) return { ok: false, granted: false, available: false };
  try {
    const { receive } = await messaging.requestPermissions();
    return { ok: true, granted: receive === 'granted', available: true };
  } catch {
    return { ok: false, granted: false, available: true };
  }
}

/** Subscribe or unsubscribe a single topic and persist the preference. Persists
 *  the preference even when the plugin is absent, so the choice is remembered and
 *  applied once Firebase is wired (via syncSubscriptions). */
export async function setTopic(topic: string, on: boolean): Promise<boolean> {
  if (!TOPIC_IDS.has(topic)) return false;
  const prefs = loadPrefs();
  const messaging = await loadMessaging();
  if (messaging) {
    try {
      if (on) await messaging.subscribeToTopic({ topic });
      else await messaging.unsubscribeFromTopic({ topic });
    } catch {
      return false; // leave prefs unchanged on a real failure
    }
  }
  if (on) prefs.add(topic);
  else prefs.delete(topic);
  savePrefs(prefs);
  return true;
}

/** Re-apply every stored opt-in to FCM (call after permission is granted / on
 *  launch). No-ops until the plugin exists. */
export async function syncSubscriptions(): Promise<void> {
  const messaging = await loadMessaging();
  if (!messaging) return;
  for (const topic of loadPrefs()) {
    try {
      await messaging.subscribeToTopic({ topic });
    } catch {
      /* one failed topic shouldn't stop the rest */
    }
  }
}
