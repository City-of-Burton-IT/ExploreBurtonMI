<script lang="ts">
  import type { Snippet } from 'svelte';
  import { registerOverlay } from './store.svelte';

  // Shared dialog shell for About / Settings / WelcomeModal / Lightbox. Owns the
  // bits every hand-rolled dialog used to duplicate: backdrop, Escape, the
  // Android hardware-back registry, focus save/move/restore, and a real focus
  // trap (Tab/Shift+Tab never leave the dialog). The caller is expected to only
  // render this component while it should be open (e.g. behind an `{#if}` or a
  // `$derived` boolean) -- mount/destroy IS the open/close signal, so all
  // lifecycle wiring below runs exactly once per open.
  //
  // Visual sizing varies per dialog (About/Settings/WelcomeModal are card-style;
  // Lightbox is a fullscreen-ish dark image viewer). Small deltas (max-width,
  // z-index, backdrop darkness, shadow, padding) are exposed as CSS custom
  // properties a caller can set via `style`; a bigger deviation (Lightbox's
  // close-button chrome + card-less content) is handled by passing an extra
  // `class` that the caller's own stylesheet targets with :global(...).
  let {
    close,
    label,
    labelledby,
    register = true,
    closeLabel = 'Close',
    class: extraClass = '',
    style: extraStyle = '',
    children,
  }: {
    close: () => void;
    label?: string;
    labelledby?: string;
    register?: boolean;
    closeLabel?: string;
    class?: string;
    style?: string;
    children: Snippet;
  } = $props();

  let dialog = $state<HTMLDivElement>();
  let closeBtn = $state<HTMLButtonElement>();
  let lastFocus: HTMLElement | null = null;

  const FOCUSABLE =
    'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function focusables(): HTMLElement[] {
    return dialog ? Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE)) : [];
  }

  function onBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) close();
  }

  // Escape closes; Tab/Shift+Tab cycle within the dialog's focusable elements
  // and never let focus escape into the background content.
  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      close();
      return;
    }
    if (e.key !== 'Tab') return;
    const els = focusables();
    if (els.length === 0) {
      e.preventDefault();
      return;
    }
    const first = els[0];
    const last = els[els.length - 1];
    const active = document.activeElement;
    if (e.shiftKey) {
      if (active === first || !dialog?.contains(active)) {
        e.preventDefault();
        last.focus();
      }
    } else if (active === last || !dialog?.contains(active)) {
      e.preventDefault();
      first.focus();
    }
  }

  // Save the trigger's focus, move focus into the dialog once mounted, and
  // restore it on close -- mirrors the queueMicrotask pattern every dialog used.
  $effect(() => {
    lastFocus = (document.activeElement as HTMLElement) ?? null;
    queueMicrotask(() => (closeBtn ?? dialog)?.focus());
    return () => {
      lastFocus?.focus?.();
    };
  });

  // Android hardware back closes this dialog first. `register` is false for
  // dialogs (About) whose open flag is instead read directly by nativeBack.ts.
  $effect(() => {
    if (register) return registerOverlay(close);
  });
</script>

<svelte:window onkeydown={onKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="backdrop {extraClass}" style={extraStyle} role="presentation" onclick={onBackdropClick}>
  <div
    bind:this={dialog}
    class="modal"
    role="dialog"
    aria-modal="true"
    aria-label={label}
    aria-labelledby={labelledby}
    tabindex="-1"
  >
    <button bind:this={closeBtn} class="close" onclick={close} aria-label={closeLabel}>&times;</button>
    {@render children()}
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: var(--modal-z, 2000);
    background: var(--modal-backdrop-bg, rgba(0, 0, 0, 0.4));
    display: grid;
    place-items: center;
    padding: var(--modal-outer-padding, 1rem);
  }
  .modal {
    position: relative;
    background: var(--modal-bg, var(--pub-surface));
    color: var(--modal-color, var(--pub-ink));
    border-radius: var(--modal-radius, var(--pub-radius-lg, 16px));
    max-width: var(--modal-max-width, 480px);
    width: 100%;
    max-height: var(--modal-max-height, calc(100% - 2rem));
    overflow-y: var(--modal-overflow, auto);
    padding: var(--modal-padding, 1.6rem 1.7rem);
    box-shadow: var(--modal-shadow, 0 1rem 3rem rgba(0, 0, 0, 0.175));
    line-height: 1.6;
  }
  .modal:focus-visible {
    outline: none;
  }
  .close {
    position: absolute;
    top: var(--modal-close-top, 0.5rem);
    right: var(--modal-close-right, 0.7rem);
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
</style>
