import type { GuideBundle, GuideSectionMeta } from '../types';
import { ICONS } from './icons';

const SECTION_TYPES = new Set<GuideSectionMeta['type']>([
  'markdown',
  'contacts',
  'meetings',
  'waste',
  'ops-status',
  'civicclerk',
  'video',
]);
const SECTION_ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE = /^[+()\d.\-\s]+$/;
const TIME = /^(?:1[0-2]|[1-9]):[0-5]\d (?:AM|PM)$/;
const VIDEO_HOSTS = new Set(['www.elocallink.tv']);
const PDF_HOSTS = new Set(['burtonmi.gov', 'www.burtonmi.gov']);

function isPlainObject(value: unknown): value is Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function isIsoDate(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return false;
  const [, year, month, day] = match.map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

function decodedPathIsSafe(value: string): boolean {
  if (value.startsWith('//') || value.includes('\\')) return false;
  try {
    const decoded = decodeURIComponent(value);
    return !decoded.split(/[/?#]/).includes('..') && !decoded.startsWith('//');
  } catch {
    return false;
  }
}

function isSafePdf(value: unknown): value is string {
  if (!isNonEmptyString(value)) return false;
  const href = value.trim();
  if (/^https:\/\//i.test(href)) {
    try {
      const url = new URL(href);
      return (
        !url.username &&
        !url.password &&
        PDF_HOSTS.has(url.hostname.toLowerCase()) &&
        url.pathname.toLowerCase().endsWith('.pdf')
      );
    } catch {
      return false;
    }
  }
  if (/^[a-z][a-z0-9+.-]*:/i.test(href) || !decodedPathIsSafe(href)) return false;
  return /^\/?[a-z0-9][a-z0-9/_-]*\.pdf$/i.test(href);
}

function isSafeVideoSrc(value: unknown): value is string {
  if (!isNonEmptyString(value)) return false;
  try {
    const url = new URL(value);
    return (
      url.protocol === 'https:' &&
      !url.username &&
      !url.password &&
      VIDEO_HOSTS.has(url.hostname.toLowerCase()) &&
      url.pathname.startsWith('/m/v/')
    );
  } catch {
    return false;
  }
}

function isSafeAssetPath(value: unknown): value is string {
  if (!isNonEmptyString(value)) return false;
  const path = value.trim();
  return (
    decodedPathIsSafe(path) &&
    /^\/[a-z0-9][a-z0-9/_-]*\.(?:avif|gif|jpe?g|png|webp)$/i.test(path)
  );
}

function duplicateError(
  seen: Set<string>,
  value: string,
  path: string,
  errors: string[],
): void {
  if (seen.has(value)) errors.push(`${path} is a duplicate keyed-list value`);
  else seen.add(value);
}

function validateContacts(raw: unknown, required: boolean, errors: string[]): void {
  if (raw === undefined) {
    if (required) errors.push('contacts.groups is required by the contacts section');
    return;
  }
  if (!isPlainObject(raw) || !Array.isArray(raw.groups)) {
    errors.push('contacts.groups must be an array');
    return;
  }
  if (!required) errors.push('contacts is present but no contacts section is registered');
  if (raw.groups.length === 0) errors.push('contacts.groups must contain at least one group');

  const groupNames = new Set<string>();
  raw.groups.forEach((groupRaw, groupIndex) => {
    const groupPath = `contacts.groups[${groupIndex}]`;
    if (!isPlainObject(groupRaw)) {
      errors.push(`${groupPath} is not an object`);
      return;
    }
    if (!isNonEmptyString(groupRaw.name)) errors.push(`${groupPath}.name is required`);
    else duplicateError(groupNames, groupRaw.name, `${groupPath}.name`, errors);

    if (!Array.isArray(groupRaw.people)) {
      errors.push(`${groupPath}.people must be an array`);
      return;
    }
    if (groupRaw.people.length === 0) errors.push(`${groupPath}.people must not be empty`);
    const people = new Set<string>();
    groupRaw.people.forEach((personRaw, personIndex) => {
      const personPath = `${groupPath}.people[${personIndex}]`;
      if (!isPlainObject(personRaw)) {
        errors.push(`${personPath} is not an object`);
        return;
      }
      const titleValid = isNonEmptyString(personRaw.title);
      const nameValid = isNonEmptyString(personRaw.name);
      if (!titleValid) errors.push(`${personPath}.title is required`);
      if (!nameValid) errors.push(`${personPath}.name is required`);
      if (titleValid && nameValid) {
        duplicateError(people, `${personRaw.name}\u0000${personRaw.title}`, personPath, errors);
      }
      if (personRaw.phone !== undefined) {
        const digits = typeof personRaw.phone === 'string' ? personRaw.phone.replace(/\D/g, '') : '';
        if (!isNonEmptyString(personRaw.phone) || !PHONE.test(personRaw.phone) || digits.length < 7 || digits.length > 15) {
          errors.push(`${personPath}.phone must be a valid phone number`);
        }
      }
      if (personRaw.email !== undefined && (!isNonEmptyString(personRaw.email) || !EMAIL.test(personRaw.email))) {
        errors.push(`${personPath}.email must be a valid email address`);
      }
      if (personRaw.committees !== undefined) {
        if (!Array.isArray(personRaw.committees)) {
          errors.push(`${personPath}.committees must be an array`);
        } else {
          const committees = new Set<string>();
          personRaw.committees.forEach((committee, committeeIndex) => {
            const committeePath = `${personPath}.committees[${committeeIndex}]`;
            if (!isNonEmptyString(committee)) errors.push(`${committeePath} must be a non-empty string`);
            else duplicateError(committees, committee, committeePath, errors);
          });
        }
      }
    });
  });
}

function validateMeetings(raw: unknown, required: boolean, errors: string[]): void {
  if (raw === undefined) {
    if (required) {
      errors.push('meetings.council is required by the meetings section');
      errors.push('meetings.boards is required by the meetings section');
    }
    return;
  }
  if (!isPlainObject(raw)) {
    errors.push('meetings must be an object');
    return;
  }
  if (!required) errors.push('meetings is present but no meetings section is registered');
  if (raw.intro !== undefined && !isNonEmptyString(raw.intro)) {
    errors.push('meetings.intro must be a non-empty string');
  }

  if (!Array.isArray(raw.council)) {
    errors.push('meetings.council must be an array');
  } else {
    if (required && raw.council.length === 0) errors.push('meetings.council must not be empty');
    const dates = new Set<string>();
    let previousDate = '';
    raw.council.forEach((meetingRaw, index) => {
      const path = `meetings.council[${index}]`;
      if (!isPlainObject(meetingRaw)) {
        errors.push(`${path} is not an object`);
        return;
      }
      if (!isIsoDate(meetingRaw.date)) errors.push(`${path}.date must be a real ISO date (YYYY-MM-DD)`);
      else {
        duplicateError(dates, meetingRaw.date, path, errors);
        if (previousDate && meetingRaw.date < previousDate) errors.push(`${path}.date must be chronological`);
        previousDate = meetingRaw.date;
      }
      if (!isNonEmptyString(meetingRaw.time) || !TIME.test(meetingRaw.time)) {
        errors.push(`${path}.time must use h:mm AM/PM`);
      }
      if (meetingRaw.alt !== undefined && typeof meetingRaw.alt !== 'boolean') {
        errors.push(`${path}.alt must be a boolean`);
      }
    });
  }

  if (!Array.isArray(raw.boards)) {
    errors.push('meetings.boards must be an array');
  } else {
    if (required && raw.boards.length === 0) errors.push('meetings.boards must not be empty');
    const boardNames = new Set<string>();
    raw.boards.forEach((boardRaw, index) => {
      const path = `meetings.boards[${index}]`;
      if (!isPlainObject(boardRaw)) {
        errors.push(`${path} is not an object`);
        return;
      }
      if (!isNonEmptyString(boardRaw.name)) errors.push(`${path}.name is required`);
      else duplicateError(boardNames, boardRaw.name, path, errors);
      if (!isNonEmptyString(boardRaw.schedule)) errors.push(`${path}.schedule is required`);
    });
  }
}

export function validateGuideBundle(raw: unknown): GuideBundle {
  if (!isPlainObject(raw)) throw new Error('guide.json is not an object');

  const errors: string[] = [];
  const sectionIds = new Set<string>();
  const markdownIds = new Set<string>();
  const singletonTypes = new Set<string>();
  let contactsRequired = false;
  let meetingsRequired = false;

  if (!Array.isArray(raw.sections)) {
    errors.push('sections must be an array');
  } else {
    if (raw.sections.length === 0) errors.push('sections must contain at least one fallback section');
    raw.sections.forEach((sectionRaw, index) => {
      const path = `sections[${index}]`;
      if (!isPlainObject(sectionRaw)) {
        errors.push(`${path} is not an object`);
        return;
      }
      const id = sectionRaw.id;
      const idValid = typeof id === 'string' && SECTION_ID.test(id);
      if (!idValid) errors.push(`${path}.id must be a non-empty URL-safe slug`);
      else duplicateError(sectionIds, id, `${path}.id`, errors);
      if (!isNonEmptyString(sectionRaw.title)) errors.push(`${path}.title is required`);

      const type = sectionRaw.type;
      const typeValid = typeof type === 'string' && SECTION_TYPES.has(type as GuideSectionMeta['type']);
      if (!typeValid) errors.push(`${path}.type is invalid`);
      if (type === 'markdown' && idValid) markdownIds.add(id);
      if (type === 'contacts') contactsRequired = true;
      if (type === 'meetings') meetingsRequired = true;
      if (type === 'contacts' || type === 'meetings') {
        if (singletonTypes.has(type)) errors.push(`${path}.type duplicates the singleton '${type}' section`);
        else singletonTypes.add(type);
      }

      if (sectionRaw.icon !== undefined) {
        if (!isNonEmptyString(sectionRaw.icon) || !Object.hasOwn(ICONS, sectionRaw.icon)) {
          errors.push(`${path}.icon is not in the guide icon registry`);
        }
      }
      if (type === 'video') {
        if (!isSafeVideoSrc(sectionRaw.src)) {
          errors.push(`${path}.src must be an HTTPS URL on an approved video host`);
        }
        if (sectionRaw.provider !== 'eLocalLink') {
          errors.push(`${path}.provider must match the approved eLocalLink host`);
        }
        if (sectionRaw.poster !== undefined && !isSafeAssetPath(sectionRaw.poster)) {
          errors.push(`${path}.poster must be a safe site-relative path`);
        }
      }
    });
  }

  if (raw.pdf !== undefined && !isSafePdf(raw.pdf)) {
    errors.push('pdf must be a safe PDF path or an approved HTTPS City URL');
  }

  if (!isPlainObject(raw.content)) {
    errors.push('content must be an object of section id -> HTML string');
  } else {
    for (const [id, html] of Object.entries(raw.content)) {
      if (typeof html !== 'string') errors.push(`content.${id} must be an HTML string`);
      if (!markdownIds.has(id)) errors.push(`content.${id} does not match a markdown section`);
    }
    for (const id of markdownIds) {
      if (typeof raw.content[id] !== 'string') errors.push(`content.${id} is required for the markdown section`);
    }
  }

  validateContacts(raw.contacts, contactsRequired, errors);
  validateMeetings(raw.meetings, meetingsRequired, errors);

  if (errors.length) throw new Error(`Invalid guide.json:\n - ${errors.join('\n - ')}`);
  return raw as unknown as GuideBundle;
}
