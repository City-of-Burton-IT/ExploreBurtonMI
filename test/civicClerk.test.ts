import { describe, expect, it } from 'vitest';
import { validateCivicClerkEvents } from '../src/lib/guide/civicClerk';

const event = {
  id: 42,
  eventName: 'City Council',
  startDateTime: '2026-07-20T19:00:00Z',
  categoryName: 'Council',
  agendaId: 7,
  mediaStreamPath: '/stream/42',
};

describe('CivicClerk response validation', () => {
  it('accepts and normalizes valid events', () => {
    expect(validateCivicClerkEvents({ value: [event] }, 'upcoming')).toEqual([event]);
    expect(
      validateCivicClerkEvents(
        { value: [{ ...event, categoryName: null, agendaId: 0, mediaStreamPath: '' }] },
        'recent',
      ),
    ).toEqual([{ id: 42, eventName: 'City Council', startDateTime: event.startDateTime }]);
  });

  it.each([
    null,
    {},
    { value: [{ ...event, id: 0 }] },
    { value: [{ ...event, eventName: '' }] },
    { value: [{ ...event, startDateTime: 'not-a-date' }] },
    { value: [event, event] },
    { value: [{ ...event, agendaId: -1 }] },
    { value: [{ ...event, mediaStreamPath: 42 }] },
  ])('rejects malformed event data: %j', (raw) => {
    expect(() => validateCivicClerkEvents(raw, 'fixture')).toThrow(/CivicClerk|fixture/i);
  });
});
