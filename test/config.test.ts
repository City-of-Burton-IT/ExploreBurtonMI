import { describe, it, expect } from 'vitest';
import { validateConfig } from '../src/lib/config';
import { validateData } from '../src/lib/data';

const validConfig = {
  project: { name: 'Explore Burton', tagline: 't' },
  map: { center: [43, -83.6], zoom: 13 },
  tiles: { url: 'https://x/{z}/{x}/{y}.png' },
};

describe('validateConfig', () => {
  it('accepts a valid config', () => {
    expect(() => validateConfig(validConfig)).not.toThrow();
  });

  it('throws when project.name is missing', () => {
    const bad = { ...validConfig, project: { tagline: 't' } };
    expect(() => validateConfig(bad)).toThrow(/project\.name/);
  });

  it('throws on a malformed map center', () => {
    const bad = { ...validConfig, map: { center: [43], zoom: 13 } };
    expect(() => validateConfig(bad)).toThrow(/map\.center/);
  });

  it('throws when tiles.url is missing', () => {
    const bad = { ...validConfig, tiles: {} };
    expect(() => validateConfig(bad)).toThrow(/tiles\.url/);
  });
});

describe('validateData', () => {
  const fc = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [-83.6, 43.0] },
        properties: { name: 'City Hall' },
      },
    ],
  };

  it('accepts a valid FeatureCollection and assigns an id', () => {
    const out = validateData(fc);
    expect(out.features).toHaveLength(1);
    expect(out.features[0].id).toBe('eb-0');
  });

  it('throws when not a FeatureCollection', () => {
    expect(() => validateData({ type: 'Nope' })).toThrow(/FeatureCollection/);
  });

  it('throws on invalid geometry', () => {
    const bad = {
      type: 'FeatureCollection',
      features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [1] }, properties: { name: 'x' } }],
    };
    expect(() => validateData(bad)).toThrow(/Point geometry/);
  });

  it('throws when a feature is missing name', () => {
    const bad = {
      type: 'FeatureCollection',
      features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [1, 2] }, properties: {} }],
    };
    expect(() => validateData(bad)).toThrow(/name/);
  });
});
