import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import {
  guideHashNeedsNormalization,
  guideAnchorFromHash,
  guideSectionFromHash,
  guideSectionHash,
} from '../src/lib/dashboards';
import { guideHeadingId, resolveGuideSection } from '../src/lib/guide/guideSections';
import type { GuideBundle } from '../src/lib/types';

const bundle = JSON.parse(readFileSync('public/guide.json', 'utf8')) as GuideBundle;

describe('Resident Guide routes', () => {
  it('selects the first valid section for the bare guide route', () => {
    const resolution = resolveGuideSection(bundle.sections, null);
    expect(resolution.section?.id).toBe(bundle.sections[0].id);
    expect(resolution.shouldNormalize).toBe(false);
    expect(guideHashNeedsNormalization('#guide', bundle.sections)).toBe(false);
  });

  it('round-trips every generated section direct link', () => {
    for (const section of bundle.sections) {
      const hash = `#${guideSectionHash(section.id)}`;
      expect(guideSectionFromHash(hash)).toBe(section.id);
      expect(resolveGuideSection(bundle.sections, section.id).section).toEqual(section);
      expect(guideHashNeedsNormalization(hash, bundle.sections)).toBe(false);
    }
  });

  it('keeps section-qualified heading anchors on the selected guide route', () => {
    const hash = `#${guideSectionHash(bundle.sections[0].id, 'city-offices')}`;
    expect(guideSectionFromHash(hash)).toBe(bundle.sections[0].id);
    expect(guideAnchorFromHash(hash)).toBe('city-offices');
    expect(guideHashNeedsNormalization(hash, bundle.sections)).toBe(false);
  });

  it('falls back and normalizes an unknown or deleted section exactly once', () => {
    const resolution = resolveGuideSection(bundle.sections, 'deleted-section');
    expect(resolution.section?.id).toBe(bundle.sections[0].id);
    expect(resolution.shouldNormalize).toBe(true);
    expect(guideHashNeedsNormalization('#guide/deleted-section', bundle.sections)).toBe(true);
    expect(
      guideHashNeedsNormalization(`#${guideSectionHash(bundle.sections[0].id)}`, bundle.sections),
    ).toBe(false);
  });

  it.each([
    '#guide/%70ermits',
    '#guide/%2e%2e',
    '#guide/trash%2Frecycling',
    '#guide/too/many/segments',
    '#guide/UPPER',
    '#guide/../permits',
    '#guide/permits?extra',
  ])('never selects an encoded or malformed section id: %s', (hash) => {
    expect(guideSectionFromHash(hash)).toBeNull();
    expect(guideHashNeedsNormalization(hash, bundle.sections)).toBe(true);
  });

  it('does not treat non-guide hashes as guide routes to normalize', () => {
    expect(guideHashNeedsNormalization('#map', bundle.sections)).toBe(false);
    expect(guideHashNeedsNormalization('#city-offices', bundle.sections)).toBe(false);
  });
});

describe('Resident Guide Markdown anchors', () => {
  it('creates stable local heading ids without changing the app hash route', () => {
    expect(guideHeadingId('City Offices')).toBe('city-offices');
    expect(guideHeadingId('Trash & Recycling')).toBe('trash-recycling');
    expect(guideHeadingId('  2026 Holiday Schedule  ')).toBe('2026-holiday-schedule');
  });
});
