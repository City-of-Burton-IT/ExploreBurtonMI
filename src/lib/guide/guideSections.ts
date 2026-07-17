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
