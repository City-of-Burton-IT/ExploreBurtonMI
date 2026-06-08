import { mount } from 'svelte'
import { Capacitor } from '@capacitor/core'
import './app.css'
import App from './App.svelte'
import { captureInstallPrompt, markInstalled, type BeforeInstallPromptEvent } from './lib/store.svelte'

// Native (Capacitor) only: keep the WebView BELOW the status bar instead of drawing
// edge-to-edge under it (which hid the top nav). Give the status bar an opaque civic
// background with light icons. No-op on the web/PWA build.
if (Capacitor.isNativePlatform()) {
  import('@capacitor/status-bar')
    .then(({ StatusBar, Style }) => {
      StatusBar.setOverlaysWebView({ overlay: false }).catch(() => {})
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
