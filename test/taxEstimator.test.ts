import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import TaxEstimator from '../src/lib/TaxEstimator.svelte';
import type { InfoEstimator } from '../src/lib/types';

const data: InfoEstimator = {
  cityRatePeriod: 'Provisional — current L-4029 pending',
  fullBillRatePeriod: '2025 published rates',
  cityMills: 13.44,
  cityLevies: [
    {
      id: 'general-operating',
      service: 'General city operations',
      authorization: 'City Charter — budget reference',
      description: 'FY2026-27 Approved Budget service line.',
      mills: 4,
      voterApproved: false,
    },
    {
      id: 'police',
      service: 'Police services',
      authorization: 'Voter approved — budget aggregate',
      description: 'FY2026-27 Approved Budget aggregate Police Levies line.',
      mills: 8.3159,
      voterApproved: true,
    },
    {
      id: 'fire',
      service: 'Fire services',
      authorization: 'Voter approved — budget reference',
      description: 'FY2026-27 Approved Budget service line.',
      mills: 0.9789,
      voterApproved: true,
    },
    {
      id: 'l4029-reconciliation',
      service: 'Unassigned difference',
      authorization: 'Pending L-4029',
      description: 'Difference between the 13.44 provisional total and 13.2948 budget service-line total.',
      mills: 0.1452,
      voterApproved: false,
    },
  ],
  districts: [{ name: 'Atherton', homestead: 41.86, nonHomestead: 59.72 }],
};

describe('TaxEstimator', () => {
  it('renders the budget service breakdown and reconciles it to the provisional City total', () => {
    const { body } = render(TaxEstimator, { props: { data } });

    expect(body).toContain('Your City of Burton taxes');
    expect(body).toContain('Provisional — current L-4029 pending');
    expect(body).toContain('<table');
    expect(body).toContain('City service');
    expect(body).toContain('Source / status');
    expect(body).toContain('General city operations');
    expect(body).toContain('Police services');
    expect(body).toContain('Fire services');
    expect(body).toContain('Unassigned difference');
    expect(body).toContain('Pending L-4029');
    expect(body).toContain('4.0000');
    expect(body).toContain('8.3159');
    expect(body).toContain('0.9789');
    expect(body).toContain('0.1452');
    expect(body).toContain('$200.00');
    expect(body).toContain('$415.80');
    expect(body).toContain('$48.95');
    expect(body).toContain('$7.26');
    expect(body).toContain('13.4');
    expect(body).toContain('$672.00');
    expect(body).toContain('9.2948 voter-approved mills');
    expect(body).toContain('do not yet identify how the 0.1452-mill difference is allocated');
  });

  it('keeps the older complete-bill estimate in a separately dated result', () => {
    const { body } = render(TaxEstimator, { props: { data } });

    expect(body).toContain('Estimated complete property-tax bill');
    expect(body).toContain('2025 published rates');
    expect(body).toContain('$2,093.00');
    expect(body).toContain('41.86 mills');
    expect(body).toContain('do not become City of Burton revenue');
    expect(body).not.toContain('Only about');
    expect(body).not.toContain('Schools &amp; other');
  });
});
