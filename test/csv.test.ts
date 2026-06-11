import { describe, it, expect } from 'vitest';
import { csvSlug, toCsv } from '../src/lib/csv';

describe('csvSlug', () => {
  it('slugifies a title to a safe filename stem', () => {
    expect(csvSlug('Largest districts (acres)')).toBe('largest-districts-acres');
  });
  it('collapses punctuation and trims dashes', () => {
    expect(csvSlug('Health & Environment')).toBe('health-environment');
  });
  it('falls back to "data" when nothing remains', () => {
    expect(csvSlug('  ***  ')).toBe('data');
  });
});

describe('toCsv', () => {
  it('joins headers + rows with CRLF', () => {
    expect(toCsv(['A', 'B'], [['1', '2'], ['3', '4']])).toBe('A,B\r\n1,2\r\n3,4');
  });
  it('quotes fields containing a comma', () => {
    expect(toCsv(['X'], [['a,b']])).toBe('X\r\n"a,b"');
  });
  it('escapes embedded quotes by doubling them', () => {
    expect(toCsv(['X'], [['say "hi"']])).toBe('X\r\n"say ""hi"""');
  });
  it('quotes fields containing a newline', () => {
    expect(toCsv(['X'], [['a\nb']])).toBe('X\r\n"a\nb"');
  });
});
