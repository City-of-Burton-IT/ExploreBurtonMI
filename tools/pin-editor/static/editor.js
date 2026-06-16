/* Burton Pin Editor -- Leaflet map + edit routing UI.
 * Pins are color-coded by source (curated vs auto-discovered). Edits accumulate in a
 * pending tray and only hit disk on Save; the id prefix decides the source file
 * server-side (see edits.py). */
'use strict';

const FIELDS = ['name', 'category', 'address', 'phone', 'website', 'hours'];
const OPT_FIELDS = ['address', 'phone', 'website', 'hours'];

const state = {
  byId: {},          // id -> working feature (geometry + properties kept live)
  orig: {},          // id -> {coords:[lng,lat], props:{...}} snapshot for undo/no-op
  markers: {},       // id -> L.marker
  categories: [],
  bbox: null,        // [minLng, minLat, maxLng, maxLat]
  pending: [],       // edit ops (the tray)
  mode: 'select',
  selectedId: null,
  addSeq: 0,
  lastSummary: '',
};

let map, boundaryLayer;

const $ = (id) => document.getElementById(id);
const isAdd = (id) => String(id).startsWith('new:');
const isCurated = (id) => /^(burton:|manual:|new:)/.test(String(id));

function toast(msg, kind) {
  const t = $('toast');
  t.textContent = msg;
  t.className = 'toast' + (kind ? ' ' + kind : '');
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { t.hidden = true; }, 3200);
}

async function getJSON(url) { return (await fetch(url)).json(); }
async function postJSON(url, body) {
  const r = await fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  return r.json();
}

/* ---- markers ---------------------------------------------------------- */

function pinClass(id) {
  let cls = isCurated(id) ? 'curated' : 'discovered';
  if (hasOp(id, 'delete')) cls += ' deleted';
  else if (hasOp(id, 'move') || hasOp(id, 'edit') || isAdd(id)) cls += ' edited';
  if (id === state.selectedId) cls += ' selected';
  return cls;
}

function icon(id) {
  return L.divIcon({
    className: '', html: `<div class="pin ${pinClass(id)}"></div>`,
    iconSize: [12, 12], iconAnchor: [6, 6],
  });
}

function refreshMarker(id) {
  const m = state.markers[id];
  if (m) m.setIcon(icon(id));
}

function addMarker(feature) {
  const [lng, lat] = feature.geometry.coordinates;
  const m = L.marker([lat, lng], {
    draggable: true, icon: icon(feature.id),
    title: feature.properties.name || feature.id,
  });
  m.on('click', () => selectPin(feature.id));
  m.on('dragend', () => onDragEnd(feature.id));
  m.addTo(map);
  state.markers[feature.id] = m;
}

function onDragEnd(id) {
  const m = state.markers[id];
  if (hasOp(id, 'delete')) {           // can't move a pin marked for deletion
    const [lng, lat] = state.byId[id].geometry.coordinates;
    m.setLatLng([lat, lng]);
    return;
  }
  const ll = m.getLatLng();
  recordMove(id, [ll.lng, ll.lat]);
}

/* ---- pending edits ---------------------------------------------------- */

function hasOp(id, op) { return state.pending.some((e) => e.id === id && e.op === op); }
function dropOps(id, op) {
  state.pending = state.pending.filter((e) => !(e.id === id && (op ? e.op === op : true)));
}

function recordMove(id, coords) {
  state.byId[id].geometry.coordinates = coords;
  if (isAdd(id)) {
    const a = state.pending.find((e) => e.op === 'add' && e.id === id);
    if (a) a.coordinates = coords;
  } else {
    dropOps(id, 'move');
    const o = state.orig[id].coords;
    const moved = Math.abs(o[0] - coords[0]) > 1e-7 || Math.abs(o[1] - coords[1]) > 1e-7;
    if (moved) state.pending.push({ op: 'move', id, coordinates: coords });
  }
  afterChange(id);
  bboxHint(coords);
}

function applyFields() {
  const id = state.selectedId;
  if (!id) return;
  const vals = {};
  FIELDS.forEach((k) => { vals[k] = $('f-' + k).value.trim(); });
  if (!vals.name || !vals.category) { toast('Name and category are required', 'err'); return; }
  const f = state.byId[id];

  if (isAdd(id)) {
    const a = state.pending.find((e) => e.op === 'add' && e.id === id);
    a.name = vals.name; a.category = vals.category; a.fields = {};
    OPT_FIELDS.forEach((k) => { if (vals[k]) a.fields[k] = vals[k]; });
    f.properties = { ...f.properties, ...vals };
  } else {
    const orig = state.orig[id].props || {};
    const changed = {};
    FIELDS.forEach((k) => { if ((vals[k] || '') !== (orig[k] || '')) changed[k] = vals[k]; });
    dropOps(id, 'edit');
    if (Object.keys(changed).length) state.pending.push({ op: 'edit', id, fields: changed });
    f.properties = { ...orig, ...changed };
  }
  state.markers[id].options.title = vals.name;
  afterChange(id);
  toast('Applied to pending changes', 'ok');
}

function deletePin() {
  const id = state.selectedId;
  if (!id) return;
  if (isAdd(id)) { removeAdd(id); return; }
  dropOps(id);                          // clear any move/edit on this pin
  state.pending.push({ op: 'delete', id });
  closePanel();
  afterChange(id);
}

function removeAdd(id) {
  dropOps(id);
  if (state.markers[id]) { map.removeLayer(state.markers[id]); delete state.markers[id]; }
  delete state.byId[id];
  closePanel();
  renderTray(); updateSaveBtn();
}

function undo(index) {
  const e = state.pending[index];
  if (!e) return;
  const id = e.id;
  if (e.op === 'add') { removeAdd(id); return; }
  state.pending.splice(index, 1);
  if (e.op === 'move') {
    state.byId[id].geometry.coordinates = state.orig[id].coords.slice();
    const [lng, lat] = state.orig[id].coords;
    if (state.markers[id]) state.markers[id].setLatLng([lat, lng]);
  } else if (e.op === 'edit') {
    state.byId[id].properties = { ...state.orig[id].props };
  }
  if (id === state.selectedId) openPanel(state.byId[id]);
  afterChange(id);
}

function afterChange(id) {
  refreshMarker(id);
  renderTray();
  updateSaveBtn();
}

/* ---- panel ------------------------------------------------------------ */

function selectPin(id) {
  const prev = state.selectedId;
  state.selectedId = id;
  if (prev && prev !== id) refreshMarker(prev);
  refreshMarker(id);
  openPanel(state.byId[id]);
}

function openPanel(feature) {
  const p = feature.properties || {};
  $('panel-title').textContent = isAdd(feature.id) ? 'New pin' : 'Edit pin';
  $('panel-id').textContent = feature.id + (isCurated(feature.id) ? '  (curated)' : '  (discovered)');
  FIELDS.forEach((k) => {
    if (k === 'category') return;
    $('f-' + k).value = p[k] || '';
  });
  const sel = $('f-category');
  sel.value = p.category || state.categories[0];
  bboxHint(feature.geometry.coordinates);
  $('panel').hidden = false;
}

function closePanel() {
  const prev = state.selectedId;
  state.selectedId = null;
  $('panel').hidden = true;
  if (prev) refreshMarker(prev);
}

function bboxHint(coords) {
  const [lng, lat] = coords;
  const b = state.bbox;
  const out = b && (lng < b[0] || lng > b[2] || lat < b[1] || lat > b[3]);
  $('panel-hint').textContent = out ? 'Warning: this location is outside the city limits.' : '';
}

/* ---- tray ------------------------------------------------------------- */

function trayLabel(e) {
  const f = state.byId[e.id];
  const name = (f && f.properties.name) || e.name || e.id;
  if (e.op === 'add') return `Add "${e.name || '(unnamed)'}"`;
  if (e.op === 'move') return `Move ${name}`;
  if (e.op === 'edit') return `Edit ${name} (${Object.keys(e.fields).join(', ')})`;
  if (e.op === 'delete') return `Delete ${name}`;
  return e.op;
}

function renderTray() {
  const ul = $('tray');
  ul.innerHTML = '';
  state.pending.forEach((e, i) => {
    const li = document.createElement('li');

    const op = document.createElement('span');
    op.className = 'op ' + e.op;       // e.op is one of add/move/edit/delete
    op.textContent = e.op;

    const label = document.createElement('span');
    label.className = 'label';
    label.textContent = trayLabel(e);
    label.title = e.id || '';          // setting .title (not innerHTML) is safe

    const btn = document.createElement('button');
    btn.className = 'undo'; btn.type = 'button'; btn.textContent = 'undo';
    btn.addEventListener('click', () => undo(i));

    li.append(op, label, btn);
    ul.appendChild(li);
  });
  $('tray-count').textContent = state.pending.length;
  $('discard-all').hidden = state.pending.length === 0;
}

function updateSaveBtn() {
  $('save').disabled = state.pending.length === 0;
}

function summarize() {
  const c = { add: 0, move: 0, edit: 0, delete: 0 };
  state.pending.forEach((e) => { c[e.op]++; });
  return Object.entries(c).filter(([, n]) => n > 0)
    .map(([op, n]) => `${n} ${op}`).join(', ');
}

/* ---- save / regenerate / publish -------------------------------------- */

async function save() {
  if (!state.pending.length) return;
  state.lastSummary = summarize();
  $('save').disabled = true;
  toast('Saving source files...', 'ok');
  const edits = state.pending.map((e) => {
    const c = { ...e };
    if (isAdd(c.id)) delete c.id;      // server assigns the manual: id
    return c;
  });
  const saved = await postJSON('/api/save', { edits });
  if (!saved.ok) { toast('Save failed: ' + (saved.error || ''), 'err'); updateSaveBtn(); return; }

  toast('Regenerating data.geojson...', 'ok');
  const reg = await postJSON('/api/regenerate', {});
  const diff = (await getJSON('/api/diff')).diff;

  let body = reg.ok
    ? `Pipeline OK. Features: ${reg.before} -> ${reg.after}\n\n${diff}`
    : `PIPELINE FAILED (exit ${reg.returncode}). Nothing will be published.\n\n${reg.stderr || reg.stdout}`;
  showModal(reg.ok ? 'Saved + regenerated' : 'Regenerate failed', body, reg.ok);

  state.pending = [];
  await reload();
}

function showModal(title, body, canPublish) {
  $('modal-title').textContent = title;
  $('modal-body').textContent = body;
  $('publish').hidden = !canPublish;
  $('modal').hidden = false;
}
function closeModal() { $('modal').hidden = true; }

async function publish() {
  $('publish').disabled = true;
  const r = await postJSON('/api/publish', { summary: state.lastSummary });
  $('publish').disabled = false;
  if (r.ok) { toast('Published: committed + pushed', 'ok'); closeModal(); }
  else if (r.committed) toast('Committed but push failed: ' + r.detail, 'err');
  else toast(`Publish failed (${r.step}): ${r.detail}`, 'err');
}

/* ---- load / reload ---------------------------------------------------- */

async function reload() {
  Object.values(state.markers).forEach((m) => map.removeLayer(m));
  state.markers = {}; state.byId = {}; state.orig = {};
  state.selectedId = null; $('panel').hidden = true;

  const data = await getJSON('/api/data');
  state.categories = data.categories;
  state.bbox = data.bbox;
  fillCategorySelect();

  data.features.forEach((f) => {
    if (!f.geometry || !f.geometry.coordinates) return;
    state.byId[f.id] = f;
    state.orig[f.id] = {
      coords: f.geometry.coordinates.slice(),
      props: { ...f.properties },
    };
    addMarker(f);
  });
  $('count').textContent = `${Object.keys(state.byId).length} pins`;
  renderTray(); updateSaveBtn();
}

function fillCategorySelect() {
  const sel = $('f-category');
  sel.innerHTML = '';
  state.categories.forEach((c) => {
    const o = document.createElement('option');
    o.value = c; o.textContent = c; sel.appendChild(o);
  });
}

function setMode(mode) {
  state.mode = mode;
  $('mode-select').classList.toggle('active', mode === 'select');
  $('mode-add').classList.toggle('active', mode === 'add');
  if (map) map.getContainer().style.cursor = mode === 'add' ? 'crosshair' : '';
}

function onMapClick(e) {
  if (state.mode !== 'add') return;
  const id = 'new:' + (++state.addSeq);
  const coords = [e.latlng.lng, e.latlng.lat];
  const f = {
    type: 'Feature', id,
    geometry: { type: 'Point', coordinates: coords },
    properties: { name: '', category: state.categories[0] },
  };
  state.byId[id] = f;
  state.orig[id] = { coords: coords.slice(), props: {} };
  state.pending.push({ op: 'add', id, name: '', category: state.categories[0], coordinates: coords, fields: {} });
  addMarker(f);
  setMode('select');
  selectPin(id);
  renderTray(); updateSaveBtn();
  toast('New pin placed -- enter name + category, then Apply', 'ok');
}

function search(q) {
  q = q.trim().toLowerCase();
  Object.entries(state.byId).forEach(([id, f]) => {
    const m = state.markers[id];
    if (!m) return;
    const hit = !q || (f.properties.name || '').toLowerCase().includes(q);
    m.setOpacity(hit ? 1 : 0.15);
  });
}

/* ---- init ------------------------------------------------------------- */

function initMap() {
  map = L.map('map', { center: [42.999, -83.616], zoom: 13 });
  L.tileLayer(
    'https://imagery.michigan.gov/server/rest/services/Michigan_imagery_public/MapServer/tile/{z}/{y}/{x}',
    { maxZoom: 19, attribution: 'State of Michigan imagery' },
  ).addTo(map);
  L.tileLayer(
    'https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}',
    { maxZoom: 19, opacity: 0.9 },
  ).addTo(map);
  map.on('click', onMapClick);

  getJSON('/api/boundary').then((b) => {
    if (b && b.type) {
      boundaryLayer = L.geoJSON(b, {
        style: { color: '#c8a24a', weight: 2, fill: false },
      }).addTo(map);
    }
  }).catch(() => {});
}

function wireUI() {
  $('mode-select').addEventListener('click', () => setMode('select'));
  $('mode-add').addEventListener('click', () => setMode('add'));
  $('reload').addEventListener('click', () => reload());
  $('apply-fields').addEventListener('click', applyFields);
  $('delete-pin').addEventListener('click', deletePin);
  $('panel-close').addEventListener('click', closePanel);
  $('save').addEventListener('click', save);
  $('discard-all').addEventListener('click', () => {
    Object.keys(state.byId).filter(isAdd).forEach(removeAdd);
    state.pending = [];
    reload();
  });
  $('publish').addEventListener('click', publish);
  $('modal-close').addEventListener('click', closeModal);
  $('search').addEventListener('input', (e) => search(e.target.value));
}

window.addEventListener('DOMContentLoaded', async () => {
  initMap();
  wireUI();
  await reload();
});
