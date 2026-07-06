import { readFileSync } from 'node:fs';
import { describe, it, expect } from 'vitest';
import { validateGuideBundle } from '../src/lib/guide/guideBundle';

const validBundle = {
  sections: [{ id: 'welcome', title: 'Welcome', type: 'markdown' }],
  content: { welcome: '<p>Hi</p>' },
};

describe('validateGuideBundle', () => {
  it('accepts a minimal valid bundle', () => {
    expect(() => validateGuideBundle(validBundle)).not.toThrow();
  });

  it('accepts the real public/guide.json', () => {
    const raw = JSON.parse(readFileSync('public/guide.json', 'utf-8'));
    expect(() => validateGuideBundle(raw)).not.toThrow();
  });

  it('accepts optional contacts and meetings when well-formed', () => {
    const bundle = {
      ...validBundle,
      contacts: {
        groups: [{ name: 'City Staff', people: [{ title: 'Mayor', name: 'Jane Doe' }] }],
      },
      meetings: {
        council: [{ date: '2026-01-08', time: '7:00 PM' }],
        boards: [{ name: 'Planning Commission', schedule: 'Monthly' }],
      },
    };
    expect(() => validateGuideBundle(bundle)).not.toThrow();
  });

  it('throws when not an object', () => {
    expect(() => validateGuideBundle(null)).toThrow(/object/);
  });

  it('throws when sections is not an array', () => {
    const bad = { ...validBundle, sections: 'nope' };
    expect(() => validateGuideBundle(bad)).toThrow(/sections/);
  });

  it('throws when a section is missing required fields', () => {
    const bad = { ...validBundle, sections: [{ id: 'x' }] };
    expect(() => validateGuideBundle(bad)).toThrow(/title/);
  });

  it('throws when a section has an invalid type', () => {
    const bad = { ...validBundle, sections: [{ id: 'x', title: 'X', type: 'bogus' }] };
    expect(() => validateGuideBundle(bad)).toThrow(/type/);
  });

  it('throws when content is not an object of strings', () => {
    const bad = { ...validBundle, content: { welcome: 123 } };
    expect(() => validateGuideBundle(bad)).toThrow(/content/);
  });

  it('throws when contacts.groups is malformed', () => {
    const bad = { ...validBundle, contacts: { groups: [{ name: 'x', people: [{ name: 'no title' }] }] } };
    expect(() => validateGuideBundle(bad)).toThrow(/people/);
  });

  it('throws when meetings.council entries lack a date or time', () => {
    const bad = { ...validBundle, meetings: { council: [{ date: '2026-01-08' }], boards: [] } };
    expect(() => validateGuideBundle(bad)).toThrow(/council/);
  });

  it('throws when meetings.boards entries lack a name or schedule', () => {
    const bad = { ...validBundle, meetings: { council: [], boards: [{ name: 'x' }] } };
    expect(() => validateGuideBundle(bad)).toThrow(/boards/);
  });
});
