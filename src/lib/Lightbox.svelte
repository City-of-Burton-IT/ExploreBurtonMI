<script lang="ts">
  import Modal from './Modal.svelte';

  // Reusable image lightbox. Call `show(src, caption)` via a bound instance.
  // Backdrop/Escape/focus-trap/Android-back all come from the shared <Modal>;
  // this component keeps only its own image-viewer chrome (dark fullscreen-ish
  // backdrop, no card background, a floating circular close button) via the
  // `lightbox` class below -- visually too different from About/Settings/
  // WelcomeModal's card style to fold into Modal's defaults, so it overrides
  // them with :global(...) instead of forcing a shared look.
  let open = $state(false);
  let src = $state('');
  let caption = $state('');

  export function show(imgSrc: string, cap = '') {
    src = imgSrc;
    caption = cap;
    open = true;
  }

  function close() {
    open = false;
  }
</script>

{#if open}
  <Modal
    {close}
    label={caption || 'Image viewer'}
    closeLabel="Close image"
    class="lightbox"
    style="--modal-max-width: 96vw; --modal-max-height: 92vh; --modal-z: 3000; --modal-backdrop-bg: rgba(0, 0, 0, 0.82); --modal-outer-padding: 1.2rem; --modal-padding: 0"
  >
    <img class="lb-img" {src} alt={caption} />
    {#if caption}<p class="lb-caption">{caption}</p>{/if}
  </Modal>
{/if}

<style>
  :global(.backdrop.lightbox .modal) {
    width: auto;
    background: none;
    box-shadow: none;
    border-radius: 0;
    color: #fff;
    overflow: visible;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }
  .lb-img {
    max-width: 96vw;
    max-height: 82vh;
    width: auto;
    height: auto;
    border-radius: var(--pub-radius-sm, 8px);
    box-shadow: 0 1rem 3rem rgba(0, 0, 0, 0.5);
  }
  .lb-caption {
    margin: 0;
    color: #fff;
    font-size: 0.88rem;
    text-align: center;
    max-width: 60ch;
  }
  :global(.backdrop.lightbox .close) {
    top: -2.6rem;
    right: 0;
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
    width: 2.1rem;
    height: 2.1rem;
    border-radius: 999px;
    font-size: 1.5rem;
  }
  :global(.backdrop.lightbox .close:hover) {
    background: rgba(255, 255, 255, 0.3);
  }
  :global(.backdrop.lightbox .close:focus-visible) {
    outline: 2px solid #fff;
    outline-offset: 2px;
    box-shadow: none;
  }
</style>
