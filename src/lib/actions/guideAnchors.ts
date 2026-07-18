import { guideHeadingId } from '../guide/guideSections';
import { guideAnchorFromHash, guideSectionFromHash } from '../dashboards';

function assignHeadingIds(node: HTMLElement): void {
  const used = new Map<string, number>();
  node.querySelectorAll<HTMLElement>('h2, h3').forEach((heading, index) => {
    const base = guideHeadingId(heading.textContent ?? '') || `section-${index + 1}`;
    const count = (used.get(base) ?? 0) + 1;
    used.set(base, count);
    heading.id = count === 1 ? base : `${base}-${count}`;
  });
}

/** Keep Markdown anchors local to the guide instead of replacing the app hash route. */
export function guideAnchors(node: HTMLElement, sectionId: string) {
  let currentSection = sectionId;
  const scrollToCurrentAnchor = () => {
    if (guideSectionFromHash(window.location.hash) !== currentSection) return;
    const id = guideAnchorFromHash(window.location.hash);
    if (!id) return;
    const heading = [...node.querySelectorAll<HTMLElement>('[id]')].find((item) => item.id === id);
    if (!heading) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    heading.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
  };
  const refresh = () => queueMicrotask(() => {
    assignHeadingIds(node);
    scrollToCurrentAnchor();
  });
  refresh();

  const onClick = (event: MouseEvent) => {
    const target = event.target instanceof Element ? event.target.closest<HTMLAnchorElement>('a[href^="#"]') : null;
    if (!target || !node.contains(target)) return;
    const href = target.getAttribute('href') ?? '';
    if (
      guideSectionFromHash(href) !== currentSection ||
      !guideAnchorFromHash(href) ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) return;
    event.preventDefault();
    if (window.location.hash === href) scrollToCurrentAnchor();
    else window.location.hash = href;
  };

  node.addEventListener('click', onClick);
  window.addEventListener('hashchange', scrollToCurrentAnchor);
  return {
    update(nextSection: string) {
      if (nextSection !== currentSection) {
        currentSection = nextSection;
        refresh();
      }
    },
    destroy() {
      node.removeEventListener('click', onClick);
      window.removeEventListener('hashchange', scrollToCurrentAnchor);
    },
  };
}
