// Push notifications (#64) -- opt-in, topic-based FCM (Firebase IS wired).
//
// Decisions (2026-06-12): opt-in only; topic-based (NO per-device token leaves
// the app, no per-resident record); topics = alerts / service / meetings;
// Android-first. Send path + approval gate live server-side (Power Automate ->
// FCM HTTP v1), see the spec.
//
// Firebase is wired (google-services.json + @capacitor-firebase/messaging + cap
// sync are done). loadMessaging() below uses a PLAIN dynamic import so Vite emits a
// real chunk that RESOLVES at runtime on device; web never reaches it (the
// isPushSupported gate), so the web initial bundle stays lean.

import { Capacitor } from '@capacitor/core';
// STATIC import so registerPlugin lands in the main entry (already loaded), NOT a
// lazy chunk. A lazy dynamic-import chunk did not load inside the Capacitor WebView,
// so the plugin never registered and push stayed inert on device (#64). The heavy
// firebase SDK is behind this plugin's own `web:` lazy factory, which only runs on
// the web platform -- and the isPushSupported() gate stops us ever calling it there,
// so the web bundle stays lean.
import { FirebaseMessaging } from '@capacitor-firebase/messaging';

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

/** The messaging plugin on native, or null on web. The plugin is statically
 *  imported (see the import note above), so on native it is always present -- no
 *  lazy chunk to fail to load. Kept async so callers don't change. */
async function loadMessaging(): Promise<FirebaseMessagingLike | null> {
  if (!isPushSupported()) return null;
  return FirebaseMessaging as unknown as FirebaseMessagingLike;
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

export interface PushDiag {
  platform: string;
  isNative: boolean;
  pluginDefined: boolean;
  available: boolean | null;
  permission: string | null;
  error: string | null;
}

function errMsg(e: unknown): string {
  if (e instanceof Error) return e.message || e.name;
  try {
    return JSON.stringify(e);
  } catch {
    return String(e);
  }
}

/** Runtime push diagnostics, surfaced in Settings so we can see ON THE DEVICE why
 *  push is or isn't available -- instead of guessing from build logs. Each step is
 *  wrapped so a throw is captured as text rather than swallowed. */
export async function pushDiagnostics(): Promise<PushDiag> {
  const diag: PushDiag = {
    platform: Capacitor.getPlatform(),
    isNative: Capacitor.isNativePlatform(),
    pluginDefined: FirebaseMessaging != null,
    available: null,
    permission: null,
    error: null,
  };
  try {
    diag.available = await isPushAvailable();
  } catch (e) {
    diag.error = `available: ${errMsg(e)}`;
  }
  if (diag.isNative && diag.pluginDefined) {
    try {
      // checkPermissions reports the current OS permission WITHOUT prompting, and
      // surfaces a "not implemented on android" error if the NATIVE plugin class is
      // missing from the build (vs the JS wrapper merely being present).
      const res = (await FirebaseMessaging.checkPermissions()) as { receive?: string };
      diag.permission = res?.receive ?? JSON.stringify(res);
    } catch (e) {
      diag.error = `${diag.error ? diag.error + ' | ' : ''}checkPermissions: ${errMsg(e)}`;
    }
  }
  return diag;
}
