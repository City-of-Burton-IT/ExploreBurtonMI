// "Report outdated information" feedback path. A mailto whose subject pre-fills
// the dashboard name so a resident's report is self-describing.
//
// NOTE: this mailbox must exist / be routed before it is live (like privacy@).
// It is a dedicated address for the Explore Burton app; change it here only.
export const FEEDBACK_EMAIL = 'explore@burtonmi.gov';

/**
 * Build a `mailto:` link for reporting outdated data. When a context (e.g. the
 * dashboard title) is given, it is appended to the subject so the report says
 * which page it came from.
 */
export function reportOutdatedMailto(context?: string): string {
  const subject = context
    ? `Explore Burton: outdated information (${context})`
    : 'Explore Burton: outdated information';
  return `mailto:${FEEDBACK_EMAIL}?subject=${encodeURIComponent(subject)}`;
}
