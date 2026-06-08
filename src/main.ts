import { mount } from 'svelte'
import './app.css'
import App from './App.svelte'
import { captureInstallPrompt, markInstalled, type BeforeInstallPromptEvent } from './lib/store.svelte'

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
