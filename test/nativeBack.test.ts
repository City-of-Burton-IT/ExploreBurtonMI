import { describe, it, expect } from 'vitest';
import { backDecision } from '../src/lib/nativeBack';

describe('backDecision (Android hardware back priority chain)', () => {
  it('closes an open overlay first, above everything else', () => {
    expect(
      backDecision({ overlay: true, about: true, detail: true, view: 'finances' }),
    ).toBe('overlay');
  });

  it('closes the About dialog before the detail sheet or a view change', () => {
    expect(
      backDecision({ overlay: false, about: true, detail: true, view: 'guide' }),
    ).toBe('about');
  });

  it('closes the place detail sheet before changing view', () => {
    expect(
      backDecision({ overlay: false, about: false, detail: true, view: 'guide' }),
    ).toBe('detail');
  });

  it('returns to the map from a dashboard view', () => {
    expect(
      backDecision({ overlay: false, about: false, detail: false, view: 'finances' }),
    ).toBe('go-map');
  });

  it('returns to the map from the guide', () => {
    expect(
      backDecision({ overlay: false, about: false, detail: false, view: 'guide' }),
    ).toBe('go-map');
  });

  it('exits when on the map with nothing open (second Back from a dashboard)', () => {
    expect(
      backDecision({ overlay: false, about: false, detail: false, view: 'map' }),
    ).toBe('exit');
  });
});
