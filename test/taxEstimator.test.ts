import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import TaxEstimator from '../src/lib/TaxEstimator.svelte';
import type { InfoEstimator } from '../src/lib/types';

const data: InfoEstimator = {
  cityRatePeriod: 'FY2026-27 adopted levy',
  fullBillRatePeriod: '2025 published rates',
  cityMills: 13.2948,
  cityLevies: [
    {
      id: 'general-operating',
      service: 'General city operations',
      authorization: 'City Charter',
      description: 'Supports general municipal services provided by the City.',
      mills: 4,
      voterApproved: false,
    },
    {
      id: 'police',
      service: 'Police services',
      authorization: 'Voter approved',
      description: 'Supports Police Department staffing and operations.',
      mills: 8.3159,
      voterApproved: true,
    },
    {
      id: 'fire',
      service: 'Fire services',
      authorization: 'Voter approved',
      description: 'Supports Fire Department services and operations.',
      mills: 0.9789,
      voterApproved: true,
    },
  ],
  districts: [{ name: 'Atherton', homestead: 41.86, nonHomestead: 59.72 }],
};

describe('TaxEstimator', () => {
  it('renders the latest City levy as a personalized service table', () => {
    const { body } = render(TaxEstimator, { props: { data } });

    expect(body).toContain('Your City of Burton taxes');
    expect(body).toContain('FY2026-27 adopted levy');
    expect(body).toContain('<table');
    expect(body).toContain('City service');
    expect(body).toContain('Who authorized it');
    expect(body).toContain('General city operations');
    expect(body).toContain('Police services');
    expect(body).toContain('Fire services');
    expect(body).toContain('City Charter');
    expect(body.match(/Voter approved/g)).toHaveLength(2);
    expect(body).toContain('4.0000');
    expect(body).toContain('8.3159');
    expect(body).toContain('0.9789');
    expect(body).toContain('$200.00');
    expect(body).toContain('$415.80');
    expect(body).toContain('$48.95');
    expect(body).toContain('$664.74');
    expect(body).toContain('9.2948 voter-approved mills');
    expect(body).toContain('$464.74');
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
