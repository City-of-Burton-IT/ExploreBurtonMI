import { describe, it, expect } from 'vitest';
import { welcomeDismissed } from '../src/lib/welcome';

describe('welcomeDismissed (first-run onboarding visibility)', () => {
  it('shows on a native/web first run (no stored flag)', () => {
    expect(welcomeDismissed(null)).toBe(false);
  });

  it('shows when the stored value is empty or anything but the flag', () => {
    expect(welcomeDismissed('')).toBe(false);
    expect(welcomeDismissed('0')).toBe(false);
    expect(welcomeDismissed('true')).toBe(false);
  });

  it('stays dismissed once the flag is set', () => {
    expect(welcomeDismissed('1')).toBe(true);
  });
});
