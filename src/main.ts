import { mount } from 'svelte'
import { Capacitor } from '@capacitor/core'
import './app.css'
import App from './App.svelte'
import ComingSoon from './lib/ComingSoon.svelte'
import { COMING_SOON_ENABLED, shouldGate } from './lib/comingSoon'
import { captureInstallPrompt, markInstalled, type BeforeInstallPromptEvent } from './lib/store.svelte'

// Native (Capacitor) only: the status-bar colour + light icons are set in the Android
// theme (styles.xml) so the WebView sits cleanly below the status bar. Reinforce the
// colour/style at runtime, but DON'T toggle overlaysWebView -- at targetSDK 34 (non
// edge-to-edge) the OS already insets the WebView, and forcing overlay there caused a
// black bar + top-toolbar glitch. No-op on the web/PWA build.
if (Capacitor.isNativePlatform()) {
  import('@capacitor/status-bar')
    .then(({ StatusBar, Style }) => {
      StatusBar.setBackgroundColor({ color: '#2c57a0' }).catch(() => {})
      StatusBar.setStyle({ style: Style.Light }).catch(() => {})
    })
    .catch(() => {})

  // Hardware back button: close an open sheet/dialog, else return to the map,
  // else exit (the WebView default is to exit from any screen).
  import('./lib/nativeBack')
    .then(({ initNativeBack }) => initNativeBack())
    .catch(() => {})
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
