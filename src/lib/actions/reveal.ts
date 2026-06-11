// Scroll-reveal Svelte action: fades-and-rises an element's direct children as
// they scroll into view. No-op (everything visible immediately) under
// prefers-reduced-motion or when IntersectionObserver is unavailable. Reusable.
//
// Usage: <div use:reveal> ...blocks... </div>
// Styling lives in app.css (.reveal-init / .revealed).

export function reveal(node: HTMLElement) {
  const reduce =
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  const targets = Array.from(node.children) as HTMLElement[];

  if (reduce || typeof IntersectionObserver === 'undefined') {
    targets.forEach((el) => el.classList.add('revealed'));
    return {};
  }

  targets.forEach((el) => el.classList.add('reveal-init'));
  const io = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) {
          (e.target as HTMLElement).classList.add('revealed');
          io.unobserve(e.target);
        }
      }
    },
    { rootMargin: '0px 0px -8% 0px', threshold: 0.04 },
  );
  targets.forEach((el) => io.observe(el));

  return {
    destroy() {
      io.disconnect();
    },
  };
}
