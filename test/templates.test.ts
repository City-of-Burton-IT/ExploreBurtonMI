import { describe, it, expect } from 'vitest';
import {
  safeExternalUrl,
  safeMailto,
  safeTel,
  directionsUrl,
  renderProperties,
  type PropertyConfig,
} from '../src/lib/templates';

describe('safeExternalUrl', () => {
  it('accepts http and https', () => {
    expect(safeExternalUrl('https://burtonmi.gov')).toBe('https://burtonmi.gov/');
    expect(safeExternalUrl('http://example.com/x')).toBe('http://example.com/x');
  });

  it('adds https to a scheme-less host', () => {
    expect(safeExternalUrl('example.com')).toBe('https://example.com/');
  });

  it('rejects javascript: and data: URLs', () => {
    expect(safeExternalUrl('javascript:alert(1)')).toBeNull();
    expect(safeExternalUrl('JavaScript:alert(1)')).toBeNull();
    expect(safeExternalUrl('data:text/html,<script>')).toBeNull();
  });

  it('rejects other schemes and empty input', () => {
    expect(safeExternalUrl('ftp://example.com')).toBeNull();
    expect(safeExternalUrl('   ')).toBeNull();
  });
});

describe('safeMailto / safeTel', () => {
  it('builds mailto for a valid email, null otherwise', () => {
    expect(safeMailto('clerk@burtonmi.gov')).toBe('mailto:clerk@burtonmi.gov');
    expect(safeMailto('not-an-email')).toBeNull();
  });

  it('builds tel from a formatted phone, null when too short', () => {
    expect(safeTel('(810) 743-1500')).toBe('tel:8107431500');
    expect(safeTel('123')).toBeNull();
  });
});

describe('directionsUrl', () => {
  it('encodes the destination address', () => {
    expect(directionsUrl('4303 S Center Rd, Burton, MI')).toBe(
      'https://www.google.com/maps/dir/?api=1&destination=4303%20S%20Center%20Rd%2C%20Burton%2C%20MI',
    );
  });
});

describe('renderProperties', () => {
  const config: PropertyConfig[] = [
    { field: 'name', label: 'Name' },
    { field: 'website', label: 'Website', format: 'url' },
    { field: 'evil', label: 'Evil', format: 'url' },
    { field: 'missing', label: 'Missing' },
  ];

  it('formats text and links, drops empty and unsafe values', () => {
    const out = renderProperties(config, {
      name: 'Burton City Hall',
      website: 'burtonmi.gov',
      evil: 'javascript:alert(1)',
    });
    expect(out).toEqual([
      { kind: 'text', label: 'Name', value: 'Burton City Hall' },
      { kind: 'link', label: 'Website', href: 'https://burtonmi.gov/', text: 'burtonmi.gov' },
    ]);
    // 'evil' dropped (unsafe url), 'missing' dropped (no value)
  });
});
