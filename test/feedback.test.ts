import { describe, it, expect } from 'vitest';
import { reportOutdatedMailto, FEEDBACK_EMAIL } from '../src/lib/feedback';

const subjectOf = (url: string): string => decodeURIComponent(url.split('?subject=')[1] ?? '');

describe('reportOutdatedMailto', () => {
  it('targets the feedback mailbox', () => {
    expect(reportOutdatedMailto('X').startsWith(`mailto:${FEEDBACK_EMAIL}?subject=`)).toBe(true);
  });

  it('pre-fills the subject with the dashboard name', () => {
    expect(subjectOf(reportOutdatedMailto('City Finances'))).toBe(
      'Explore Burton: outdated information (City Finances)',
    );
  });

  it('uses a generic subject when no context is given', () => {
    expect(subjectOf(reportOutdatedMailto())).toBe('Explore Burton: outdated information');
  });

  it('percent-encodes special characters so they do not break the mailto', () => {
    const url = reportOutdatedMailto('Health & Environment');
    // a raw & in the subject would start a new mailto field; it must be encoded
    expect(url.split('?subject=')[1]).not.toContain('&');
    expect(subjectOf(url)).toBe('Explore Burton: outdated information (Health & Environment)');
  });
});
