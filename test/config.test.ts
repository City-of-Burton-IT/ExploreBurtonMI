import { readFileSync } from 'node:fs';
import { describe, it, expect } from 'vitest';
import { validateConfig } from '../src/lib/config';
import { validateData } from '../src/lib/data';

const validConfig = {
  project: { name: 'Explore Burton', tagline: 't' },
  data: { source: 'data.geojson' },
  map: {
    center: [43, -83.6],
    zoom: 13,
    maxZoom: 18,
    minZoom: 10,
    maxBounds: [
      [42.85, -83.85],
      [43.15, -83.4],
    ],
    previewAttribute: 'name',
  },
  tiles: { url: 'https://x/{z}/{x}/{y}.png', attribution: 'Attribution' },
  categoryField: 'category',
  categories: { Government: { color: '#111' } },
  properties: [{ field: 'address', label: 'Address' }],
  facets: { category: { title: 'Category', type: 'single' } },
  list: ['name', 'address'],
  search: { keys: ['name', 'address'] },
};

describe('validateConfig', () => {
  it('accepts a valid config', () => {
    expect(() => validateConfig(validConfig)).not.toThrow();
  });

  it('accepts the real public/config.json', () => {
    const raw = JSON.parse(readFileSync('public/config.json', 'utf-8'));
    expect(() => validateConfig(raw)).not.toThrow();
  });

  it('throws when project.name is missing', () => {
    const bad = { ...validConfig, project: { tagline: 't' } };
    expect(() => validateConfig(bad)).toThrow(/project\.name/);
  });

  it('throws when project.tagline is missing', () => {
    const bad = { ...validConfig, project: { name: 'x' } };
    expect(() => validateConfig(bad)).toThrow(/project\.tagline/);
  });

  it('throws when data.source is missing', () => {
    const bad = { ...validConfig, data: {} };
    expect(() => validateConfig(bad)).toThrow(/data\.source/);
  });

  it('throws on a malformed map center', () => {
    const bad = { ...validConfig, map: { ...validConfig.map, center: [43] } };
    expect(() => validateConfig(bad)).toThrow(/map\.center/);
  });

  it('throws when map.maxZoom or map.minZoom is not a number', () => {
    const bad = { ...validConfig, map: { ...validConfig.map, maxZoom: '18' } };
    expect(() => validateConfig(bad)).toThrow(/map\.maxZoom/);
  });

  it('throws on a malformed map.maxBounds', () => {
    const bad = { ...validConfig, map: { ...validConfig.map, maxBounds: [[42.85, -83.85]] } };
    expect(() => validateConfig(bad)).toThrow(/map\.maxBounds/);
  });

  it('throws when map.previewAttribute is missing', () => {
    const bad = { ...validConfig, map: { ...validConfig.map, previewAttribute: '' } };
    expect(() => validateConfig(bad)).toThrow(/map\.previewAttribute/);
  });

  it('throws when tiles.url is missing', () => {
    const bad = { ...validConfig, tiles: { attribution: 'a' } };
    expect(() => validateConfig(bad)).toThrow(/tiles\.url/);
  });

  it('throws when tiles.attribution is missing', () => {
    const bad = { ...validConfig, tiles: { url: 'https://x' } };
    expect(() => validateConfig(bad)).toThrow(/tiles\.attribution/);
  });

  it('throws when categoryField is missing', () => {
    const bad = { ...validConfig, categoryField: '' };
    expect(() => validateConfig(bad)).toThrow(/categoryField/);
  });

  it('throws when categories is not an object', () => {
    const bad = { ...validConfig, categories: [] };
    expect(() => validateConfig(bad)).toThrow(/categories/);
  });

  it('throws when a categories entry has no color', () => {
    const bad = { ...validConfig, categories: { Government: {} } };
    expect(() => validateConfig(bad)).toThrow(/categories/);
  });

  it('throws when properties is not an array', () => {
    const bad = { ...validConfig, properties: {} };
    expect(() => validateConfig(bad)).toThrow(/properties/);
  });

  it('throws when a properties entry is missing field or label', () => {
    const bad = { ...validConfig, properties: [{ field: 'address' }] };
    expect(() => validateConfig(bad)).toThrow(/properties/);
  });

  it('throws when facets is not an object', () => {
    const bad = { ...validConfig, facets: [] };
    expect(() => validateConfig(bad)).toThrow(/facets/);
  });

  it('throws when a facets entry has an invalid type', () => {
    const bad = { ...validConfig, facets: { category: { title: 'Category', type: 'multi' } } };
    expect(() => validateConfig(bad)).toThrow(/facets/);
  });

  it('throws when list is not an array', () => {
    const bad = { ...validConfig, list: 'name' };
    expect(() => validateConfig(bad)).toThrow(/list/);
  });

  it('throws when search.keys is not an array', () => {
    const bad = { ...validConfig, search: {} };
    expect(() => validateConfig(bad)).toThrow(/search\.keys/);
  });

  it('accepts optional fields left out (dataLayers, boundary, submit, etc.)', () => {
    expect(() => validateConfig(validConfig)).not.toThrow();
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
