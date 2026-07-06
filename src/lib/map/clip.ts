/** Build a CSS clip-path polygon (in element-relative %) from a boundary GeoJSON
 *  so an image overlay can be clipped to the city shape. Percentages scale with
 *  the element, so the clip tracks Leaflet's zoom/pan automatically. */
export function boundaryClipPath(
  geojson: { type: string; geometry?: { type: string; coordinates: number[][][] }; coordinates?: number[][][] },
  bounds: [[number, number], [number, number]],
): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const geom: any = (geojson as any).type === 'Feature' ? (geojson as any).geometry : geojson;
  const ring: number[][] | null =
    geom?.type === 'Polygon'
      ? geom.coordinates[0]
      : geom?.type === 'MultiPolygon'
        ? geom.coordinates[0][0]
        : null;
  if (!ring) return '';
  const [[south, west], [north, east]] = bounds;
  const pts = ring.map(([lng, lat]: number[]) => {
    const x = ((lng - west) / (east - west)) * 100;
    const y = ((north - lat) / (north - south)) * 100;
    return `${x.toFixed(2)}% ${y.toFixed(2)}%`;
  });
  return `polygon(${pts.join(', ')})`;
}
