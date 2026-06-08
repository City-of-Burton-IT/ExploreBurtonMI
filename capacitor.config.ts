import type { CapacitorConfig } from '@capacitor/cli';

// Capacitor wraps the existing static web build (webDir = dist) in a native shell.
// appId is the permanent Play Store / bundle identifier (reverse of explore.burtonmi.gov).
const config: CapacitorConfig = {
  appId: 'gov.burtonmi.explore',
  appName: 'Explore Burton',
  webDir: 'dist',
};

export default config;
