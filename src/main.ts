import { mount } from 'svelte'
import { Capacitor } from '@capacitor/core'
import './app.css'
import App from './App.svelte'
import ComingSoon from './lib/ComingSoon.svelte'
import { COMING_SOON_ENABLED, shouldGate } from './lib/comingSoon'
import { captureInstallPrompt, markInstalled, initTheme, type BeforeInstallPromptEvent } from './lib/store.svelte'

// Apply the saved theme (#61) before mounting so there's no flash of the wrong
// theme. Runs for the holding page and the app alike.
initTheme()

// Native (Capacitor) only. The status bar is now handled by the theme layer
// (applyResolvedTheme in store.svelte.ts, called from initTheme above): real
// edge-to-edge (#30) draws the WebView under a transparent status bar with
// theme-aware icon colour. No-op on the web/PWA build.
if (Capacitor.isNativePlatform()) {
  // Hardware back button: close an open sheet/dialog, else return to the map,
  // else exit (the WebView default is to exit from any screen).
  import('./lib/nativeBack')
    .then(({ initNativeBack }) => initNativeBack())
    .catch((err) => console.warn('[main] nativeBack init failed:', err))

  // App Links: route a shared explore.burtonmi.gov link to the matching view.
  import('./lib/deepLinks')
    .then(({ initDeepLinks }) => initDeepLinks())
    .catch((err) => console.warn('[main] deepLinks init failed:', err))

  // Push runtime (#64): create the notification channel + wire the foreground
  // banner and tap-to-deep-link listeners. Subscriptions/permission stay opt-in
  // via Settings; this only sets up handling for messages that arrive.
  import('./lib/push')
    .then(({ initPushRuntime }) => initPushRuntime())
    .catch((err) => console.warn('[main] push init failed:', err))
}

// COMING-SOON SOFT LAUNCH (web only)
// While COMING_SOON_ENABLED is on, keep search engines off the public web build.
// Native app: no SEO surface, skip. Googlebot renders JS and honors this tag.
// (To open the site fully at launch: flip COMING_SOON_ENABLED in lib/comingSoon.ts.)
if (COMING_SOON_ENABLED && !Capacitor.isNativePlatform()) {
  const robots = document.createElement('meta')
  robots.name = 'robots'
  robots.content = 'noindex, nofollow'
  document.head.appendChild(robots)
}

const target = document.getElementById('app')!

let app
if (shouldGate()) {
  // Public web visitor without the access phrase -> holding page only.
  // The real app (and its data loading) never starts. The native app and any
  // unlocked device skip this branch entirely.
  app = mount(ComingSoon, { target })
} else {
  // Capture the install offer as early as possible -- the browser can fire
  // beforeinstallprompt before the app finishes mounting.
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    captureInstallPrompt(e as BeforeInstallPromptEvent)
  })
  window.addEventListener('appinstalled', () => markInstalled())

  app = mount(App, { target })
}

export default app
