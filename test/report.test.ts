import { describe, it, expect, vi } from 'vitest';
import {
  PHOTO_BASE64_MAX,
  buildReportPayload,
  inCity,
  submitReport,
  validateReport,
  type ReportInput,
} from '../src/lib/report';

const valid = (over: Partial<ReportInput> = {}): ReportInput => ({
  category: 'Pothole',
  lat: 43.002,
  lng: -83.632,
  description: 'Big pothole near the intersection',
  ...over,
});

describe('inCity', () => {
  it('accepts a point inside Burton and rejects points outside', () => {
    expect(inCity(43.002, -83.632)).toBe(true);
    expect(inCity(42.0, -83.632)).toBe(false);
    expect(inCity(43.002, -84.5)).toBe(false);
  });
});

describe('validateReport', () => {
  it('accepts a complete report', () => {
    expect(validateReport(valid())).toEqual([]);
  });

  it('accepts every published category, including Blight (#67)', () => {
    for (const c of ['Pothole', 'Blight', 'Sign', 'Drainage', 'Streetlight', 'Other'] as const) {
      expect(validateReport(valid({ category: c }))).toEqual([]);
    }
  });

  it('requires a category and a pin', () => {
    expect(validateReport(valid({ category: '' }))).not.toEqual([]);
    expect(validateReport(valid({ lat: null, lng: null }))).not.toEqual([]);
  });

  it('rejects a pin outside the city with a specific message', () => {
    const problems = validateReport(valid({ lat: 42.0 }));
    expect(problems.join(' ')).toMatch(/outside the City of Burton/);
  });

  it('photo, description, and contact are optional', () => {
    expect(validateReport(valid({ description: '', photoBase64: '' }))).toEqual([]);
  });

  it('rejects an oversized photo', () => {
    expect(validateReport(valid({ photoBase64: 'x'.repeat(PHOTO_BASE64_MAX + 1) }))).not.toEqual([]);
  });
});

describe('buildReportPayload', () => {
  it('sends coords as strings and always carries the honeypot', () => {
    const p = buildReportPayload(valid());
    expect(p.lat).toBe('43.002');
    expect(p.lng).toBe('-83.632');
    expect(p.hp).toBe('');
  });

  it('drops empty optional fields', () => {
    const p = buildReportPayload(valid({ description: ' ', contactName: '' }));
    expect('description' in p).toBe(false);
    expect('contactName' in p).toBe(false);
  });
});

describe('submitReport', () => {
  it('posts text/plain JSON like the suggest path', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    const result = await submitReport('https://example.test/hook', { a: '1' }, fetchFn);
    expect(result.ok).toBe(true);
    const [, init] = fetchFn.mock.calls[0];
    expect(init.headers['Content-Type']).toBe('text/plain');
  });
});
