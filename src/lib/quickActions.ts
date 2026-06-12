// Guide-section targets for the native quick-actions row (#57). Kept here, not
// inline in QuickActions.svelte, so a test can assert each id still exists in the
// Resident Guide index -- a renamed section would otherwise silently dead-link
// the action with no build error (the ids are plain strings).
export const QUICK_ACTION_GUIDE_SECTIONS = {
  waste: 'pickup-schedule',
  meetings: 'meetings',
  contact: 'contacts',
} as const;
