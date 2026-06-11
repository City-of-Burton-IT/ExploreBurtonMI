// Make every <img> inside a container click/keyboard-activatable to open a
// lightbox. Works with build-rendered markdown images (no markup changes needed).
// Pass the lightbox open(src, caption) callback as the action parameter.

type OpenFn = (src: string, caption: string) => void;

export function lightboxImages(node: HTMLElement, open: OpenFn) {
  const enhance = () => {
    node.querySelectorAll('img').forEach((img) => {
      if (img.dataset.lb) return;
      img.dataset.lb = '1';
      img.setAttribute('tabindex', '0');
      img.setAttribute('role', 'button');
      img.setAttribute('aria-label', `View larger: ${img.alt || 'image'}`);
      img.style.cursor = 'zoom-in';
    });
  };

  const openFrom = (t: EventTarget | null) => {
    if (t instanceof HTMLImageElement) {
      open(t.currentSrc || t.src, t.alt);
      return true;
    }
    return false;
  };

  const onClick = (e: MouseEvent) => {
    if (openFrom(e.target)) e.preventDefault();
  };
  const onKeydown = (e: KeyboardEvent) => {
    if ((e.key === 'Enter' || e.key === ' ') && e.target instanceof HTMLImageElement) {
      e.preventDefault();
      openFrom(e.target);
    }
  };

  enhance();
  node.addEventListener('click', onClick);
  node.addEventListener('keydown', onKeydown);

  return {
    update(next: OpenFn) {
      open = next;
    },
    destroy() {
      node.removeEventListener('click', onClick);
      node.removeEventListener('keydown', onKeydown);
    },
  };
}
