import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import GuideNav from '../src/lib/guide/GuideNav.svelte';
import type { GuideSectionMeta } from '../src/lib/types';

const sections: GuideSectionMeta[] = [
  { id: 'welcome', title: 'Welcome', type: 'markdown', icon: 'welcome' },
  { id: 'contacts', title: 'Staff & Council', type: 'contacts', icon: 'contacts' },
];

describe('GuideNav', () => {
  it('renders route navigation with one current section and distinct footer actions', () => {
    const { body } = render(GuideNav, {
      props: {
        sections,
        activeId: 'contacts',
        pdf: 'resident-guide.pdf',
        onSelect: () => {},
        onAbout: () => {},
      },
    });

    expect(body).toContain('<nav');
    expect(body).toContain('aria-label="Resident Guide sections"');
    expect(body).toContain('aria-current="page"');
    expect((body.match(/aria-current="page"/g) ?? []).length).toBe(1);
    expect(body).toContain('Staff &amp; Council');
    expect(body).toContain('About this site &amp; credits');
    expect(body).toContain('href="resident-guide.pdf"');
    expect(body).toContain('target="_blank"');
    expect(body).toContain('rel="noopener noreferrer"');
    expect(body).not.toContain('role="tablist"');
    expect(body).not.toContain('role="tab"');
  });
});
