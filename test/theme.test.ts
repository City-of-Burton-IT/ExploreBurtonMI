import { describe, it, expect } from 'vitest';
import { loadThemePref, resolveTheme } from '../src/lib/theme';

describe('loadThemePref', () => {
  it('defaults to light (dark is opt-in, never forced)', () => {
    expect(loadThemePref(null)).toBe('light');
    expect(loadThemePref('')).toBe('light');
    expect(loadThemePref('nonsense')).toBe('light');
  });

  it('accepts the three valid prefs', () => {
    expect(loadThemePref('system')).toBe('system');
    expect(loadThemePref('light')).toBe('light');
    expect(loadThemePref('dark')).toBe('dark');
  });
});

describe('resolveTheme', () => {
  it('honors an explicit light/dark choice regardless of OS', () => {
    expect(resolveTheme('light', true)).toBe('light');
    expect(resolveTheme('dark', false)).toBe('dark');
  });

  it('follows the OS when pref is system', () => {
    expect(resolveTheme('system', true)).toBe('dark');
    expect(resolveTheme('system', false)).toBe('light');
  });
});
