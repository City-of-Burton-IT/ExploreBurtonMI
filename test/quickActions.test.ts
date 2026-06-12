import { describe, it, expect } from 'vitest';
import { QUICK_ACTION_GUIDE_SECTIONS } from '../src/lib/quickActions';
import guideIndex from '../content/guide/index.json';

// The quick-actions row routes into Resident Guide sections by id. Guard against a
// renamed/removed section silently dead-linking an action (the ids are strings).
describe('quick-action guide-section targets exist in the guide index', () => {
  const ids = new Set((guideIndex.sections as { id: string }[]).map((s) => s.id));

  for (const [action, sectionId] of Object.entries(QUICK_ACTION_GUIDE_SECTIONS)) {
    it(`"${action}" -> section "${sectionId}" exists`, () => {
      expect(ids.has(sectionId)).toBe(true);
    });
  }
});
