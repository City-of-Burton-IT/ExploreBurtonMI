import { describe, it, expect, vi } from 'vitest';
import {
  buildPayload,
  validateSuggestion,
  submitSuggestion,
  type SuggestInput,
} from '../src/lib/suggest';

const valid = (over: Partial<SuggestInput> = {}): SuggestInput => ({
  changeType: 'Fix listing',
  businessName: 'Test Cafe',
  listingId: 'osm-1',
  newPhone: '(810) 555-0100',
  contactName: 'Pat Owner',
  contactPhoneEmail: 'pat@example.com',
  contactRelationship: 'Owner',
  ...over,
});

describe('validateSuggestion', () => {
  it('accepts a complete fix-listing request', () => {
    expect(validateSuggestion(valid())).toEqual([]);
  });

  it('requires the business name and full contact block', () => {
    const problems = validateSuggestion(
      valid({ businessName: ' ', contactName: '', contactPhoneEmail: '', contactRelationship: '' }),
    );
    expect(problems).toHaveLength(4);
  });

  it('rejects an unknown change type', () => {
    expect(validateSuggestion(valid({ changeType: '' }))).not.toEqual([]);
  });

  it('requires an address for add-new and moved, but not for fix or closed', () => {
    expect(validateSuggestion(valid({ changeType: 'Add my business', newAddress: '' }))).not.toEqual([]);
    expect(validateSuggestion(valid({ changeType: 'Moved', newAddress: '' }))).not.toEqual([]);
    expect(validateSuggestion(valid({ changeType: 'Add my business', newAddress: '1 Main St' }))).toEqual([]);
    expect(validateSuggestion(valid({ changeType: 'Permanently closed', newAddress: '' }))).toEqual([]);
  });

  it('rejects over-long fields', () => {
    expect(validateSuggestion(valid({ newPhone: 'x'.repeat(256) }))).not.toEqual([]);
    expect(validateSuggestion(valid({ details: 'x'.repeat(2001) }))).not.toEqual([]);
    expect(validateSuggestion(valid({ details: 'x'.repeat(2000) }))).toEqual([]);
  });
});

describe('buildPayload', () => {
  it('trims fields and drops empty optionals', () => {
    const p = buildPayload(valid({ businessName: '  Test Cafe  ', newWebsite: '   ' }));
    expect(p.businessName).toBe('Test Cafe');
    expect('newWebsite' in p).toBe(false);
  });

  it('always carries the (empty) honeypot so the flow can tell form from script', () => {
    expect(buildPayload(valid()).hp).toBe('');
  });
});

describe('submitSuggestion', () => {
  it('posts text/plain JSON and resolves ok on 200', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    const result = await submitSuggestion('https://example.test/hook', { a: '1' }, fetchFn);
    expect(result.ok).toBe(true);
    const [, init] = fetchFn.mock.calls[0];
    expect(init.method).toBe('POST');
    expect(init.headers['Content-Type']).toBe('text/plain');
    expect(JSON.parse(init.body)).toEqual({ a: '1' });
  });

  it('maps 400 to a "missing information" message', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ ok: false, status: 400 });
    const result = await submitSuggestion('https://example.test/hook', {}, fetchFn);
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/required information/);
  });

  it('never throws on network failure', async () => {
    const fetchFn = vi.fn().mockRejectedValue(new TypeError('offline'));
    const result = await submitSuggestion('https://example.test/hook', {}, fetchFn);
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/online/);
  });
});
