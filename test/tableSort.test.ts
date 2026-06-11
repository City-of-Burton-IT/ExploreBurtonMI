import { describe, it, expect } from 'vitest';
import { numericValue, sortRows } from '../src/lib/tableSort';

const rows = (...vals: string[][]) => vals.map((cells) => ({ cells }));
const col0 = (rs: { cells: string[] }[]) => rs.map((r) => r.cells[0]);

describe('numericValue', () => {
  it('parses plain, comma, currency, percent, and unit-suffixed numbers', () => {
    expect(numericValue('3,841')).toBe(3841);
    expect(numericValue('$1,234')).toBe(1234);
    expect(numericValue('54%')).toBe(54);
    expect(numericValue('918 ac')).toBe(918);
    expect(numericValue('15,000/day')).toBe(15000);
    expect(numericValue('1971')).toBe(1971);
  });
  it('returns null for non-numeric cells', () => {
    expect(numericValue('R-1A')).toBeNull();
    expect(numericValue('Good')).toBeNull();
    expect(numericValue('n/a')).toBeNull();
    expect(numericValue('')).toBeNull();
  });
});

describe('sortRows', () => {
  it('sorts a numeric column ascending and descending by value (not lexically)', () => {
    const rs = rows(['9'], ['100'], ['20']);
    expect(col0(sortRows(rs, 0, 'asc'))).toEqual(['9', '20', '100']);
    expect(col0(sortRows(rs, 0, 'desc'))).toEqual(['100', '20', '9']);
  });

  it('handles comma/unit numbers numerically', () => {
    const rs = rows(['1,000 ac'], ['90 ac'], ['250 ac']);
    expect(col0(sortRows(rs, 0, 'desc'))).toEqual(['1,000 ac', '250 ac', '90 ac']);
  });

  it('sorts a text column lexicographically', () => {
    const rs = rows(['Poor'], ['Fair'], ['Good']);
    expect(col0(sortRows(rs, 0, 'asc'))).toEqual(['Fair', 'Good', 'Poor']);
  });

  it('keeps non-numeric cells last in a numeric column', () => {
    const rs = rows(['10'], ['n/a'], ['5']);
    expect(col0(sortRows(rs, 0, 'asc'))).toEqual(['5', '10', 'n/a']);
    expect(col0(sortRows(rs, 0, 'desc'))).toEqual(['10', '5', 'n/a']);
  });

  it('is stable for equal keys (preserves input order)', () => {
    const rs = [
      { cells: ['5'], id: 'a' },
      { cells: ['5'], id: 'b' },
    ];
    expect(sortRows(rs, 0, 'asc').map((r) => r.id)).toEqual(['a', 'b']);
  });
});
