// Validation for public/guide.json (built by tools/build_guide.mjs). Fails
// LOUDLY on a malformed bundle rather than letting Guide.svelte destructure
// undefined fields -- mirrors validateData/validateConfig's style.

import type { GuideBundle, GuideSectionMeta } from '../types';

const SECTION_TYPES = new Set([
  'markdown',
  'contacts',
  'meetings',
  'waste',
  'ops-status',
  'civicclerk',
  'video',
]);

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

export function validateGuideBundle(raw: unknown): GuideBundle {
  const errors: string[] = [];
  const b = raw as Partial<GuideBundle>;

  if (!b || typeof b !== 'object') {
    throw new Error('guide.json is not an object');
  }

  if (!Array.isArray(b.sections)) {
    errors.push('sections must be an array');
  } else {
    b.sections.forEach((s, i) => {
      const sec = s as Partial<GuideSectionMeta> | null | undefined;
      if (!sec || typeof sec !== 'object') {
        errors.push(`sections[${i}] is not an object`);
        return;
      }
      if (!sec.id) errors.push(`sections[${i}].id is required`);
      if (!sec.title) errors.push(`sections[${i}].title is required`);
      if (!sec.type || !SECTION_TYPES.has(sec.type)) {
        errors.push(`sections[${i}].type is invalid`);
      }
    });
  }

  if (!isPlainObject(b.content) || Object.values(b.content).some((v) => typeof v !== 'string')) {
    errors.push('content must be an object of section id -> HTML string');
  }

  if (b.contacts !== undefined) {
    if (!isPlainObject(b.contacts) || !Array.isArray((b.contacts as { groups?: unknown }).groups)) {
      errors.push('contacts.groups must be an array');
    } else {
      const groups = (b.contacts as { groups: unknown[] }).groups;
      groups.forEach((g, i) => {
        const group = g as { name?: unknown; people?: unknown } | null | undefined;
        if (!group || typeof group !== 'object') {
          errors.push(`contacts.groups[${i}] is not an object`);
          return;
        }
        if (!group.name) errors.push(`contacts.groups[${i}].name is required`);
        if (!Array.isArray(group.people)) {
          errors.push(`contacts.groups[${i}].people must be an array`);
        } else {
          group.people.forEach((p, j) => {
            const person = p as { title?: unknown; name?: unknown } | null | undefined;
            if (!person || typeof person !== 'object' || !person.title || !person.name) {
              errors.push(`contacts.groups[${i}].people[${j}] must have a title and a name`);
            }
          });
        }
      });
    }
  }

  if (b.meetings !== undefined) {
    if (!isPlainObject(b.meetings)) {
      errors.push('meetings must be an object');
    } else {
      const m = b.meetings as { council?: unknown; boards?: unknown };
      if (!Array.isArray(m.council)) {
        errors.push('meetings.council must be an array');
      } else {
        m.council.forEach((c, i) => {
          const meeting = c as { date?: unknown; time?: unknown } | null | undefined;
          if (!meeting || typeof meeting !== 'object' || !meeting.date || !meeting.time) {
            errors.push(`meetings.council[${i}] must have a date and a time`);
          }
        });
      }
      if (!Array.isArray(m.boards)) {
        errors.push('meetings.boards must be an array');
      } else {
        m.boards.forEach((brd, i) => {
          const board = brd as { name?: unknown; schedule?: unknown } | null | undefined;
          if (!board || typeof board !== 'object' || !board.name || !board.schedule) {
            errors.push(`meetings.boards[${i}] must have a name and a schedule`);
          }
        });
      }
    }
  }

  if (errors.length) {
    throw new Error(`Invalid guide.json:\n - ${errors.join('\n - ')}`);
  }
  return b as GuideBundle;
}
