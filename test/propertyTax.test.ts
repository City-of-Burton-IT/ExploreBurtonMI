import { describe, expect, it } from 'vitest';
import {
  normaliseTaxableValue,
  roundedCents,
  sumLevyMills,
  taxForMills,
} from '../src/lib/propertyTax';

const levies = [
  { mills: 4, voterApproved: false },
  { mills: 8.3159, voterApproved: true },
  { mills: 0.9789, voterApproved: true },
];

describe('property-tax calculations', () => {
  it('calculates City service amounts without dropping mill precision', () => {
    expect(taxForMills(50_000, 4)).toBe(200);
    expect(taxForMills(50_000, 8.3159)).toBeCloseTo(415.795, 6);
    expect(taxForMills(50_000, 0.9789)).toBeCloseTo(48.945, 6);
    expect(taxForMills(50_000, sumLevyMills(levies))).toBeCloseTo(664.74, 6);
  });

  it('totals only voter-approved levies when requested', () => {
    expect(sumLevyMills(levies)).toBeCloseTo(13.2948, 6);
    expect(sumLevyMills(levies, true)).toBeCloseTo(9.2948, 6);
    expect(taxForMills(50_000, sumLevyMills(levies, true))).toBeCloseTo(464.74, 6);
  });

  it('normalises blank, negative, and non-finite taxable values to zero', () => {
    expect(normaliseTaxableValue(undefined)).toBe(0);
    expect(normaliseTaxableValue(null)).toBe(0);
    expect(normaliseTaxableValue(-1)).toBe(0);
    expect(normaliseTaxableValue(Number.NaN)).toBe(0);
    expect(normaliseTaxableValue(Number.POSITIVE_INFINITY)).toBe(0);
  });

  it('rounds display values to integer cents', () => {
    expect(roundedCents(415.795)).toBe(41_580);
    expect(roundedCents(48.945)).toBe(4_895);
    expect(roundedCents(664.74)).toBe(66_474);
  });
});
