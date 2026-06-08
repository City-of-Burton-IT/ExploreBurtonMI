import { mount } from 'svelte'
import { Capacitor } from '@capacitor/core'
import './app.css'
import App from './App.svelte'
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
}

// Capture the install offer as early as possible -- the browser can fire
// beforeinstallprompt before the app finishes mounting.
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault()
  captureInstallPrompt(e as BeforeInstallPromptEvent)
})
window.addEventListener('appinstalled', () => markInstalled())

const app = mount(App, {
  target: document.getElementById('app')!,
})

export default app
