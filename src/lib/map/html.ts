// Leaflet bindTooltip/bindPopup render string content as HTML. Feature names come
// from OpenStreetMap/Overture (community-editable), so escape them to prevent a
// crafted name (e.g. "<img onerror=...>") from executing as DOM XSS.
export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c] as string,
  );
}
