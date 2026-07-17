import { readFileSync } from 'node:fs';
import { describe, it, expect } from 'vitest';
import { validateGuideBundle } from '../src/lib/guide/guideBundle';

const validBundle = {
  sections: [{ id: 'welcome', title: 'Welcome', type: 'markdown' }],
  content: { welcome: '<p>Hi</p>' },
};

function withSection(section: Record<string, unknown>, extra: Record<string, unknown> = {}) {
  return { sections: [section], content: {}, ...extra };
}

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
      sections: [
        ...validBundle.sections,
        { id: 'contacts', title: 'Contacts', type: 'contacts' },
        { id: 'meetings', title: 'Meetings', type: 'meetings' },
      ],
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

  it.each(['', 'two words', 'UPPER', '../escape', 'encoded%2Fslash']) (
    'throws when a section id is not a URL-safe slug: %s',
    (id) => {
      const bad = { ...validBundle, sections: [{ id, title: 'Bad', type: 'markdown' }] };
      expect(() => validateGuideBundle(bad)).toThrow(/sections\[0\]\.id/);
    },
  );

  it('throws when section ids are duplicated', () => {
    const bad = {
      sections: [
        { id: 'welcome', title: 'Welcome', type: 'markdown' },
        { id: 'welcome', title: 'Again', type: 'markdown' },
      ],
      content: { welcome: '<p>Hi</p>' },
    };
    expect(() => validateGuideBundle(bad)).toThrow(/sections\[1\]\.id.*duplicate/);
  });

  it('throws when sections is empty because the first section is the route fallback', () => {
    expect(() => validateGuideBundle({ sections: [], content: {} })).toThrow(/sections.*at least one/);
  });

  it('throws when a section icon is unknown', () => {
    const bad = {
      ...validBundle,
      sections: [{ ...validBundle.sections[0], icon: 'not-in-the-registry' }],
    };
    expect(() => validateGuideBundle(bad)).toThrow(/sections\[0\]\.icon/);
  });

  it.each(['constructor', 'toString', '__proto__']) (
    'does not accept inherited object names as icons: %s',
    (icon) => {
      const bad = { ...validBundle, sections: [{ ...validBundle.sections[0], icon }] };
      expect(() => validateGuideBundle(bad)).toThrow(/sections\[0\]\.icon/);
    },
  );

  it('throws when content is not an object of strings', () => {
    const bad = { ...validBundle, content: { welcome: 123 } };
    expect(() => validateGuideBundle(bad)).toThrow(/content/);
  });

  it('throws when a markdown section has no matching content entry', () => {
    expect(() => validateGuideBundle({ ...validBundle, content: {} })).toThrow(
      /content\.welcome.*required/,
    );
  });

  it('throws when content has an orphan or non-markdown key', () => {
    const bad = { ...validBundle, content: { welcome: '<p>Hi</p>', orphan: '<p>No</p>' } };
    expect(() => validateGuideBundle(bad)).toThrow(/content\.orphan.*does not match/);
  });

  it('validates the PDF destination', () => {
    expect(() => validateGuideBundle({ ...validBundle, pdf: 'resident-guide.pdf' })).not.toThrow();
    expect(() => validateGuideBundle({ ...validBundle, pdf: '//evil.example/guide.pdf' })).toThrow(
      /pdf/,
    );
    expect(() => validateGuideBundle({ ...validBundle, pdf: 'javascript:alert(1)' })).toThrow(
      /pdf/,
    );
  });

  it('requires complete, allowlisted video metadata', () => {
    const video = { id: 'tour', title: 'Tour', type: 'video' };
    expect(() => validateGuideBundle(withSection(video))).toThrow(/sections\[0\]\.src/);
    expect(() =>
      validateGuideBundle(
        withSection(
          { ...video, src: 'https://www.elocallink.tv/m/v/watch', provider: 'eLocalLink' },
        ),
      ),
    ).not.toThrow();
    expect(() =>
      validateGuideBundle(
        withSection({ ...video, src: 'https://evil.example/embed', provider: 'Unknown' }),
      ),
    ).toThrow(/sections\[0\]\.src/);
    expect(() =>
      validateGuideBundle(
        withSection({
          ...video,
          src: 'https://user:secret@www.elocallink.tv/m/v/watch',
          provider: 'eLocalLink',
        }),
      ),
    ).toThrow(/sections\[0\]\.src/);
    expect(() =>
      validateGuideBundle(
        withSection({
          ...video,
          src: 'https://www.elocallink.tv/unapproved/watch',
          provider: 'eLocalLink',
        }),
      ),
    ).toThrow(/sections\[0\]\.src/);
  });

  it('rejects unsafe or non-image video poster paths', () => {
    const video = {
      id: 'tour',
      title: 'Tour',
      type: 'video',
      src: 'https://www.elocallink.tv/m/v/watch',
      provider: 'eLocalLink',
    };
    expect(() => validateGuideBundle(withSection({ ...video, poster: '/tour.webp' }))).not.toThrow();
    expect(() => validateGuideBundle(withSection({ ...video, poster: ' javascript:alert(1)' }))).toThrow(/poster/);
    expect(() => validateGuideBundle(withSection({ ...video, poster: '/tour.html' }))).toThrow(/poster/);
  });

  it.each(['contacts', 'meetings'])('rejects duplicate singleton %s sections', (type) => {
    const section = { id: type, title: type, type };
    const extra =
      type === 'contacts'
        ? { contacts: { groups: [{ name: 'Staff', people: [{ title: 'Clerk', name: 'Jane' }] }] } }
        : {
            meetings: {
              council: [{ date: '2026-01-01', time: '7:00 PM' }],
              boards: [{ name: 'Planning', schedule: 'Monthly' }],
            },
          };
    const bad = { sections: [section, { ...section, id: `${type}-again` }], content: {}, ...extra };
    expect(() => validateGuideBundle(bad)).toThrow(/singleton/);
  });

  it('throws when contacts.groups is malformed', () => {
    const bad = { ...validBundle, contacts: { groups: [{ name: 'x', people: [{ name: 'no title' }] }] } };
    expect(() => validateGuideBundle(bad)).toThrow(/people/);
  });

  it('requires contacts data when a contacts section is registered', () => {
    const bad = withSection({ id: 'contacts', title: 'Contacts', type: 'contacts' });
    expect(() => validateGuideBundle(bad)).toThrow(/contacts\.groups/);
  });

  it('validates every optional contact field and keyed-list uniqueness', () => {
    const base = withSection(
      { id: 'contacts', title: 'Contacts', type: 'contacts' },
      {
        contacts: {
          groups: [
            {
              name: 'Staff',
              people: [
                {
                  title: 'Clerk',
                  name: 'Jane Doe',
                  phone: '(810) 555-0100',
                  email: 'jane@burtonmi.gov',
                  committees: ['Elections'],
                },
              ],
            },
          ],
        },
      },
    );
    expect(() => validateGuideBundle(base)).not.toThrow();

    const badEmail = structuredClone(base);
    badEmail.contacts.groups[0].people[0].email = 'not-an-email';
    expect(() => validateGuideBundle(badEmail)).toThrow(/contacts\.groups\[0\]\.people\[0\]\.email/);

    const badPhone = structuredClone(base);
    badPhone.contacts.groups[0].people[0].phone = 'call me';
    expect(() => validateGuideBundle(badPhone)).toThrow(/contacts\.groups\[0\]\.people\[0\]\.phone/);

    const duplicateCommittee = structuredClone(base);
    duplicateCommittee.contacts.groups[0].people[0].committees.push('Elections');
    expect(() => validateGuideBundle(duplicateCommittee)).toThrow(/committees\[1\].*duplicate/);

    const duplicatePerson = structuredClone(base);
    duplicatePerson.contacts.groups[0].people.push(
      structuredClone(duplicatePerson.contacts.groups[0].people[0]),
    );
    expect(() => validateGuideBundle(duplicatePerson)).toThrow(/people\[1\].*duplicate/);
  });

  it('throws when meetings.council entries lack a date or time', () => {
    const bad = { ...validBundle, meetings: { council: [{ date: '2026-01-08' }], boards: [] } };
    expect(() => validateGuideBundle(bad)).toThrow(/council/);
  });

  it('throws when meetings.boards entries lack a name or schedule', () => {
    const bad = { ...validBundle, meetings: { council: [], boards: [{ name: 'x' }] } };
    expect(() => validateGuideBundle(bad)).toThrow(/boards/);
  });

  it('requires meetings data when a meetings section is registered', () => {
    const bad = withSection({ id: 'meetings', title: 'Meetings', type: 'meetings' });
    expect(() => validateGuideBundle(bad)).toThrow(/meetings\.council/);
  });

  it('validates meeting dates, flags, and keyed-list uniqueness', () => {
    const base = withSection(
      { id: 'meetings', title: 'Meetings', type: 'meetings' },
      {
        meetings: {
          intro: 'Schedule',
          council: [{ date: '2026-02-02', time: '7:00 PM', alt: false }],
          boards: [{ name: 'Planning Commission', schedule: 'Monthly' }],
        },
      },
    );
    expect(() => validateGuideBundle(base)).not.toThrow();

    const impossibleDate = structuredClone(base);
    impossibleDate.meetings.council[0].date = '2026-02-30';
    expect(() => validateGuideBundle(impossibleDate)).toThrow(/meetings\.council\[0\]\.date/);

    const badAlt = structuredClone(base);
    badAlt.meetings.council[0].alt = 'yes';
    expect(() => validateGuideBundle(badAlt)).toThrow(/meetings\.council\[0\]\.alt/);

    const duplicateDate = structuredClone(base);
    duplicateDate.meetings.council.push({ date: '2026-02-02', time: '8:00 PM', alt: false });
    expect(() => validateGuideBundle(duplicateDate)).toThrow(/council\[1\].*duplicate/);

    const duplicateBoard = structuredClone(base);
    duplicateBoard.meetings.boards.push({ name: 'Planning Commission', schedule: 'Quarterly' });
    expect(() => validateGuideBundle(duplicateBoard)).toThrow(/boards\[1\].*duplicate/);

    const unsorted = structuredClone(base);
    unsorted.meetings.council.push({ date: '2026-01-01', time: '7:00 PM', alt: false });
    expect(() => validateGuideBundle(unsorted)).toThrow(/council\[1\]\.date.*chronological/);
  });
});
