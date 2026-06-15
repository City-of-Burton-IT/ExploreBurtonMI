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
import { showPushBanner } from './store.svelte';
import { applyRoute } from './deepLinks';

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
  return loadMessaging() !== null; // sync check -- never await the plugin proxy
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

/** The messaging plugin on native, or null on web.
 *
 *  SYNCHRONOUS BY DESIGN -- this MUST NOT be async and the returned proxy MUST NOT
 *  be awaited or flowed through a Promise. The Capacitor plugin object is a Proxy
 *  that turns ANY property access into a native method call, including `.then`. If
 *  the proxy is returned from an async fn, awaited, or passed to Promise.resolve/
 *  race, the Promise machinery probes `.then`, treats the proxy as a thenable, and
 *  calls `proxy.then(resolve, reject)` -- a bogus native call that NEVER resolves,
 *  so the await hangs forever (this is what made push appear permanently inert: the
 *  native plugin worked, but `await loadMessaging()` hung). Return it directly; only
 *  await the real method results (requestPermissions/subscribeToTopic/...). (#64) */
function loadMessaging(): FirebaseMessagingLike | null {
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
  const messaging = loadMessaging();
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
  const messaging = loadMessaging();
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
  const messaging = loadMessaging();
  if (!messaging) return;
  for (const topic of loadPrefs()) {
    try {
      await messaging.subscribeToTopic({ topic });
    } catch {
      /* one failed topic shouldn't stop the rest */
    }
  }
}

const CHANNEL_ID = 'city_updates';

/** Wire the push RUNTIME on native: create the default Android notification channel
 *  and register the foreground + tap listeners. Call ONCE at startup (main.ts);
 *  no-op on web. Only real plugin METHODS are awaited here -- never the proxy. */
export async function initPushRuntime(): Promise<void> {
  if (!isPushSupported()) return;
  // Default channel: a named, high-importance home for notifications (also silences
  // the "Missing Default Notification Channel" warning). Referenced by the manifest
  // meta-data `default_notification_channel_id`. Idempotent.
  try {
    await FirebaseMessaging.createChannel({
      id: CHANNEL_ID,
      name: 'City updates',
      description: 'Emergency alerts, service disruptions, and meeting reminders.',
      importance: 4, // HIGH -> heads-up
      visibility: 1, // shown on the lock screen
    });
  } catch {
    /* createChannel is Android-only / older API -> ignore */
  }
  // Foreground: Android does NOT raise a tray notification while the app is open,
  // so surface an in-app banner instead.
  try {
    await FirebaseMessaging.addListener('notificationReceived', (event) => {
      const n = event?.notification;
      if (!n) return;
      const url = n.data && typeof (n.data as Record<string, unknown>).url === 'string'
        ? ((n.data as Record<string, unknown>).url as string)
        : null;
      showPushBanner({ title: n.title ?? 'City of Burton', body: n.body ?? '', url });
    });
  } catch {
    /* listener unsupported -> no foreground banner */
  }
  // Tap (a tray notification OR the in-app banner): route to the message's url.
  try {
    await FirebaseMessaging.addListener('notificationActionPerformed', (event) => {
      const data = event?.notification?.data as Record<string, unknown> | undefined;
      if (data && typeof data.url === 'string') applyRoute(data.url);
    });
  } catch {
    /* listener unsupported */
  }
  // Re-apply saved topic subscriptions (covers a reinstall, or a permission grant
  // that landed after setTopic first ran).
  syncSubscriptions();
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

/** Sync push facts -- safe to render IMMEDIATELY, can never hang. */
export function pushSyncInfo(): { platform: string; isNative: boolean; pluginDefined: boolean } {
  return {
    platform: Capacitor.getPlatform(),
    isNative: Capacitor.isNativePlatform(),
    pluginDefined: FirebaseMessaging != null,
  };
}

/** Race a promise against a timeout so a hanging native bridge call surfaces as
 *  'TIMEOUT' rather than blackholing the whole readout. */
function withTimeout<T>(p: Promise<T>, ms: number): Promise<T | 'TIMEOUT'> {
  return Promise.race([
    p,
    new Promise<'TIMEOUT'>((resolve) => setTimeout(() => resolve('TIMEOUT'), ms)),
  ]);
}

/** Async push probes, each time-boxed (3s). Surfaced in Settings so we can see ON
 *  THE DEVICE why push is/ isn't available -- including WHICH call hangs -- instead
 *  of guessing from build logs. */
export async function pushDiagnostics(): Promise<PushDiag> {
  const diag: PushDiag = { ...pushSyncInfo(), available: null, permission: null, error: null };
  try {
    diag.available = loadMessaging() !== null; // sync -- never await the proxy
  } catch (e) {
    diag.error = `available: ${errMsg(e)}`;
  }
  if (diag.isNative && diag.pluginDefined) {
    try {
      // checkPermissions reports the OS permission WITHOUT prompting; a "not
      // implemented" error means the native plugin class is missing, a timeout means
      // the native bridge call hung.
      const r = await withTimeout(FirebaseMessaging.checkPermissions(), 3000);
      if (r === 'TIMEOUT') diag.error = `${diag.error ? diag.error + ' | ' : ''}checkPermissions: timeout`;
      else diag.permission = (r as { receive?: string })?.receive ?? JSON.stringify(r);
    } catch (e) {
      diag.error = `${diag.error ? diag.error + ' | ' : ''}checkPermissions: ${errMsg(e)}`;
    }
  }
  return diag;
}
