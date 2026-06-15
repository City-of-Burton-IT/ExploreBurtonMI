<script lang="ts">
  import { Capacitor } from '@capacitor/core';
  import { App } from '@capacitor/app';
  import { ui, closeSettings, registerOverlay, setTheme } from './store.svelte';
  import { THEME_PREFS, type ThemePref } from './theme';
  import NotificationSettings from './NotificationSettings.svelte';
  import { pushDiagnostics, type PushDiag } from './push';

  // Settings dialog (cog in the menu bar): the single home for resident
  // preferences -- Appearance (#61) + Notifications (#64). Credits/privacy stay in
  // About. Modal mechanics mirror About / WelcomeModal (Escape, backdrop, Android
  // back via registerOverlay, focus the close button on open).

  const themeLabel = (p: ThemePref): string =>
    p === 'system' ? 'System' : p === 'light' ? 'Light' : 'Dark';

  let closeBtn = $state<HTMLButtonElement>();
  let lastFocus: HTMLElement | null = null;

  // App version + push diagnostics, loaded when the dialog opens. Shown in a small
  // footer so we can read the actual build + why push is/ isn't live ON the device.
  let appVersion = $state('');
  let diag = $state<PushDiag | null>(null);

  $effect(() => {
    if (!ui.settingsOpen) return;
    if (Capacitor.isNativePlatform()) {
      App.getInfo()
        .then((i) => (appVersion = `${i.version} (${i.build})`))
        .catch(() => (appVersion = 'unknown'));
    } else {
      appVersion = 'web';
    }
    pushDiagnostics()
      .then((d) => (diag = d))
      .catch((e) => (diag = { platform: '?', isNative: false, pluginDefined: false, available: null, permission: null, error: String(e) }));
  });

  $effect(() => {
    if (ui.settingsOpen) {
      lastFocus = (document.activeElement as HTMLElement) ?? null;
      queueMicrotask(() => closeBtn?.focus());
    }
  });

  // Android hardware back closes Settings before changing the view / exiting.
  $effect(() => {
    if (ui.settingsOpen) return registerOverlay(closeSettings);
  });

  function close() {
    closeSettings();
    lastFocus?.focus?.();
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
  }
</script>

<svelte:window onkeydown={ui.settingsOpen ? onKeydown : undefined} />

{#if ui.settingsOpen}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="backdrop" role="presentation" onclick={(e) => { if (e.target === e.currentTarget) close(); }}>
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="settings-title" tabindex="-1">
      <button bind:this={closeBtn} class="close" onclick={close} aria-label="Close">&times;</button>
      <h2 id="settings-title">Settings</h2>

      <div class="row">
        <span class="row-label">Appearance</span>
        <div class="seg-group" role="group" aria-label="Appearance / theme">
          {#each THEME_PREFS as p (p)}
            <button
              class="seg"
              class:on={ui.theme === p}
              aria-pressed={ui.theme === p}
              onclick={() => setTheme(p)}>{themeLabel(p)}</button>
          {/each}
        </div>
      </div>

      <hr />

      <NotificationSettings />

      <hr />

      <div class="diag">
        <div class="diag-line"><strong>Version</strong> {appVersion || '...'}</div>
        {#if diag}
          <div class="diag-line">
            <strong>Push</strong>
            platform={diag.platform}; native={diag.isNative ? 'yes' : 'no'};
            plugin={diag.pluginDefined ? 'yes' : 'no'};
            available={diag.available === null ? '?' : diag.available ? 'yes' : 'no'};
            permission={diag.permission ?? '-'}
          </div>
          {#if diag.error}
            <div class="diag-line diag-err">error: {diag.error}</div>
          {/if}
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    display: grid;
    place-items: center;
    z-index: 2000;
    padding: 1rem;
  }
  .modal {
    position: relative;
    background: var(--pub-surface);
    color: var(--pub-ink);
    border-radius: var(--pub-radius-lg);
    max-width: 460px;
    width: 100%;
    max-height: calc(100% - 2rem);
    overflow-y: auto;
    padding: 1.6rem 1.7rem;
    box-shadow: 0 1rem 3rem rgba(0, 0, 0, 0.175);
    line-height: 1.6;
  }
  .close {
    position: absolute;
    top: 0.5rem;
    right: 0.7rem;
    border: none;
    background: none;
    font-size: 1.6rem;
    line-height: 1;
    cursor: pointer;
    color: var(--pub-muted);
  }
  .close:hover {
    color: var(--civic-blue);
  }
  .close:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: var(--pub-radius-sm, 8px);
  }
  h2 {
    margin: 0 1.5rem 0.8rem 0;
    font-family: var(--font-head);
    font-weight: 700;
    color: var(--civic-blue);
  }
  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin: 0.2rem 0 0.6rem;
    flex-wrap: wrap;
  }
  .row-label {
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--pub-ink);
  }
  .seg-group {
    display: inline-flex;
    border: 1px solid var(--pub-border);
    border-radius: 999px;
    overflow: hidden;
  }
  .seg {
    border: none;
    background: none;
    color: var(--pub-muted, #5c5c5c);
    font-family: var(--font-body);
    font-size: 0.82rem;
    font-weight: 600;
    padding: 0.35rem 0.85rem;
    cursor: pointer;
    transition: background var(--motion-duration), color var(--motion-duration);
  }
  .seg + .seg {
    border-left: 1px solid var(--pub-border);
  }
  .seg:hover {
    color: var(--civic-blue);
  }
  .seg.on {
    background: var(--civic-accent-bg);
    color: #fff;
  }
  .seg:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  hr {
    border: none;
    border-top: 2px dashed var(--civic-green);
    margin: 1rem 0;
  }
  .diag {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.72rem;
    color: var(--pub-muted, #5c5c5c);
    word-break: break-word;
  }
  .diag-line {
    margin: 0.15rem 0;
  }
  .diag-err {
    color: var(--pub-error);
  }
</style>
