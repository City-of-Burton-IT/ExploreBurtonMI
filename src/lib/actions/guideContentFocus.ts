/** Restore a useful focus target when browser history replaces focused guide content. */
export function guideContentFocus(node: HTMLElement, sectionId: string) {
  let currentSection = sectionId;
  return {
    update(nextSection: string) {
      if (nextSection === currentSection) return;
      const focused = document.activeElement;
      const shouldFocus = focused === document.body || (focused instanceof Node && node.contains(focused));
      currentSection = nextSection;
      if (!shouldFocus) return;
      queueMicrotask(() => {
        const heading = node.querySelector<HTMLElement>(':scope > h2');
        if (!heading) return;
        heading.tabIndex = -1;
        heading.focus({ preventScroll: true });
      });
    },
  };
}
