import type { GuideSectionMeta, GuideSectionType } from '../types';

function assertNever(value: never): never {
  throw new Error(`Unregistered guide section: ${JSON.stringify(value)}`);
}

/** Single exhaustive registration point for every Resident Guide renderer. */
export function guideRenderer(section: GuideSectionMeta): GuideSectionType {
  switch (section.type) {
    case 'markdown':
    case 'contacts':
    case 'meetings':
    case 'waste':
    case 'ops-status':
    case 'civicclerk':
    case 'video':
      return section.type;
    default:
      return assertNever(section);
  }
}

export function usesGenericOfflineBadge(type: GuideSectionType): boolean {
  return type !== 'waste' && type !== 'civicclerk';
}

export function resolveGuideSection(
  sections: GuideSectionMeta[],
  requestedId: string | null,
): { section: GuideSectionMeta | null; shouldNormalize: boolean } {
  const first = sections[0] ?? null;
  if (requestedId === null) return { section: first, shouldNormalize: false };
  const match = sections.find((section) => section.id === requestedId) ?? null;
  return { section: match ?? first, shouldNormalize: match === null && first !== null };
}

export function guideHeadingId(text: string): string {
  return text
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/&/g, ' ')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}
