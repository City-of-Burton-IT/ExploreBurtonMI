// First-run welcome / onboarding visibility.
//
// One source of truth for "has the visitor seen the welcome yet?", shared by the
// web first-visit modal (#36) and the native first-launch onboarding (#59 reuses
// the same modal + copy -- no duplicate component). On a Capacitor native first
// launch the WebView's localStorage is empty, so this returns false and the modal
// shows once; dismissing writes the flag and it never shows again.

export const WELCOME_STORAGE_KEY = 'eb-welcome-dismissed';

/** Whether the welcome modal has already been dismissed. A missing or unreadable
 *  value means "not seen yet" -> show it once. */
export function welcomeDismissed(raw: string | null): boolean {
  return raw === '1';
}
