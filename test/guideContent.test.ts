import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import GuideContent from '../src/lib/guide/GuideContent.svelte';
import { guideRenderer, usesGenericOfflineBadge } from '../src/lib/guide/guideSections';
import { ui } from '../src/lib/store.svelte';
import type { GuideBundle, GuideSectionMeta } from '../src/lib/types';

const sections: GuideSectionMeta[] = [
  { id: 'welcome', title: 'Welcome', type: 'markdown', icon: 'welcome' },
  { id: 'contacts', title: 'Staff & Council', type: 'contacts', icon: 'contacts' },
];

describe('GuideContent', () => {
  it('composes the active heading and trusted Markdown body', () => {
    const bundle: GuideBundle = {
      sections,
      content: { welcome: '<p>Welcome, neighbor.</p>' },
      contacts: { groups: [] },
    };
    const { body } = render(GuideContent, {
      props: { section: sections[0], bundle, openImage: () => {} },
    });

    expect(body).toContain('<h2');
    expect(body).toContain('Welcome');
    expect(body).toContain('<p>Welcome, neighbor.</p>');
  });

  it('registers every section type at one exhaustive dispatch point', () => {
    const examples: GuideSectionMeta[] = [
      { id: 'markdown', title: 'Markdown', type: 'markdown' },
      { id: 'contacts', title: 'Contacts', type: 'contacts' },
      { id: 'meetings', title: 'Meetings', type: 'meetings' },
      { id: 'waste', title: 'Waste', type: 'waste' },
      { id: 'ops', title: 'Operations', type: 'ops-status' },
      { id: 'clerk', title: 'Clerk', type: 'civicclerk' },
      {
        id: 'video',
        title: 'Video',
        type: 'video',
        src: 'https://www.elocallink.tv/m/v/watch',
        provider: 'eLocalLink',
      },
    ];
    expect(examples.map(guideRenderer)).toEqual([
      'markdown',
      'contacts',
      'meetings',
      'waste',
      'ops-status',
      'civicclerk',
      'video',
    ]);
  });

  it('suppresses only the generic badge for self-badged widgets', () => {
    expect(usesGenericOfflineBadge('waste')).toBe(false);
    expect(usesGenericOfflineBadge('civicclerk')).toBe(false);
    expect(usesGenericOfflineBadge('markdown')).toBe(true);
    expect(usesGenericOfflineBadge('video')).toBe(true);
  });

  it('renders exactly one offline badge for generic and self-badged sections', () => {
    const originalOnline = ui.online;
    ui.online = false;
    try {
      const markdownBundle: GuideBundle = {
        sections: [sections[0]],
        content: { welcome: '<p>Welcome.</p>' },
      };
      const markdown = render(GuideContent, {
        props: { section: sections[0], bundle: markdownBundle, openImage: () => {} },
      }).body;
      expect((markdown.match(/Offline: showing saved info/g) ?? []).length).toBe(1);

      const wasteSection: GuideSectionMeta = { id: 'waste', title: 'Waste', type: 'waste' };
      const wasteBundle: GuideBundle = { sections: [wasteSection], content: {} };
      const waste = render(GuideContent, {
        props: { section: wasteSection, bundle: wasteBundle, openImage: () => {} },
      }).body;
      expect((waste.match(/Offline: showing your saved pickup schedule/g) ?? []).length).toBe(1);
      expect(waste).not.toContain('Offline: showing saved info');
    } finally {
      ui.online = originalOnline;
    }
  });

  it('does not create a third-party iframe before video activation', () => {
    const video: GuideSectionMeta = {
      id: 'video',
      title: 'Video Tour',
      type: 'video',
      src: 'https://www.elocallink.tv/m/v/watch',
      provider: 'eLocalLink',
    };
    const bundle: GuideBundle = { sections: [video], content: {} };
    const body = render(GuideContent, {
      props: { section: video, bundle, openImage: () => {} },
    }).body;

    expect(body).toContain('Play Video Tour');
    expect(body).not.toContain('<iframe');
    expect(body).not.toContain('src="https://www.elocallink.tv');
  });
});
