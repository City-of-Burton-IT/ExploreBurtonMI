<script lang="ts">
  import type { AppConfig } from './types';
  import { ui, closeReport, startReportPin } from './store.svelte';
  import {
    REPORT_CATEGORIES,
    type ReportCategory,
    type ReportInput,
    PHOTO_BASE64_MAX,
    buildReportPayload,
    validateReport,
    submitReport,
  } from './report';
  import { newToken, trackUrl } from './track';
  import { loadAddressPoints, nearestAddress } from './reverseGeocode';
  import Modal from './Modal.svelte';
  import TrackLinkPanel from './TrackLinkPanel.svelte';
  import './forms.css';

  // "Report an issue" (#14): pin + optional photo/notes -> the private DPW
  // triage queue. Never published; this is a report, not an emergency line.
  // Modal mechanics (Escape, backdrop, Android back, focus save/trap/restore)
  // live in the shared <Modal>; this component keeps only the field logic +
  // its own dialog sizing. Pin-drop mode (see below) hides the dialog by
  // toggling `open` off, which unmounts <Modal> -- Modal's own effect then
  // restores focus to whatever opened the dialog, and since this component
  // itself never unmounts, the in-progress field values (address, category,
  // etc.) survive the round trip untouched.

  let { config }: { config: AppConfig } = $props();

  const open = $derived(ui.report.open && !!config.report?.url);
  const hasPin = $derived(ui.report.lat != null && ui.report.lng != null);

  let category = $state<ReportCategory | ''>('Pothole');
  let address = $state('');
  // #71: whether the current `address` was auto-filled from the dropped pin
  // (vs typed by the resident). Used so re-dropping the pin updates an
  // auto-filled address but never clobbers one the resident typed.
  let addressAutoFilled = $state(false);
  let addressLookupBusy = $state(false);
  let lastLookupKey = '';
  let description = $state('');
  let photoBase64 = $state('');
  let photoName = $state('');
  let photoError = $state('');
  let contactName = $state('');
  let contactInfo = $state('');
  let hp = $state('');

  let phase = $state<'form' | 'submitting' | 'done'>('form');
  let problems = $state<string[]>([]);
  let submitError = $state('');
  // Resident tracking link set on a successful submit (#status); token generated
  // client-side and sent with the payload so the flow can store + email it.
  let trackLink = $state('');

  // Reset only when the modal opens FRESH. "Fresh" = it was fully closed (not
  // just hidden for pin mode, which must keep the in-progress fields).
  let wasActive = false;
  $effect(() => {
    const active = open || ui.report.pinMode;
    if (active && !wasActive) reset();
    wasActive = active;
  });
  function reset() {
    category = 'Pothole';
    address = '';
    addressAutoFilled = false;
    addressLookupBusy = false;
    lastLookupKey = '';
    description = '';
    photoBase64 = '';
    photoName = '';
    photoError = '';
    contactName = '';
    contactInfo = '';
    hp = '';
    phase = 'form';
    problems = [];
    submitError = '';
    trackLink = '';
  }

  function fullClose() {
    closeReport();
  }

  // #71: reverse-geocode the dropped pin to the nearest known address, fully
  // on-device (the resident's coords never leave the device pre-submission).
  // Fills the Address field unless the resident typed one themselves; silent
  // no-op when offline, when no city address is within range, or when the
  // committed table isn't configured -- the manual field always works.
  $effect(() => {
    const lat = ui.report.lat;
    const lng = ui.report.lng;
    const source = config.addressPoints?.source;
    if (lat == null || lng == null || !source) return;
    // Preserve an address the resident typed (non-empty + not auto-filled).
    if (address.trim() !== '' && !addressAutoFilled) return;
    const key = `${lat},${lng}`;
    if (key === lastLookupKey) return;
    lastLookupKey = key;
    addressLookupBusy = true;
    loadAddressPoints(source).then((points) => {
      addressLookupBusy = false;
      // The pin may have moved again while the table loaded -- ignore stale hits.
      if (ui.report.lat !== lat || ui.report.lng !== lng) return;
      // The resident may have typed an address during the load -- don't clobber it.
      if (address.trim() !== '' && !addressAutoFilled) return;
      const hit = nearestAddress(lat, lng, points);
      if (hit) {
        address = hit.address;
        addressAutoFilled = true;
      }
    });
  });

  // Resize the chosen photo to <=1600px JPEG on-device; only the resized copy
  // is ever uploaded. Any failure just drops the photo (it is optional).
  async function onPhotoChange(e: Event) {
    photoError = '';
    photoBase64 = '';
    photoName = '';
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;
    try {
      const bitmap = await createImageBitmap(file);
      const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(bitmap.width * scale));
      canvas.height = Math.max(1, Math.round(bitmap.height * scale));
      const ctx = canvas.getContext('2d');
      if (!ctx) throw new Error('no canvas');
      ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      bitmap.close();
      const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
      const b64 = dataUrl.slice(dataUrl.indexOf(',') + 1);
      if (b64.length > PHOTO_BASE64_MAX) {
        photoError = 'That photo is too large even after resizing. Try another.';
        return;
      }
      photoBase64 = b64;
      photoName = (file.name || 'photo').replace(/\.[^.]*$/, '') + '.jpg';
    } catch {
      photoError = 'Could not read that photo. You can submit without one.';
    }
  }

  function currentInput(): ReportInput {
    return {
      category,
      lat: ui.report.lat,
      lng: ui.report.lng,
      address,
      description,
      photoBase64,
      photoName,
      contactName,
      contactInfo,
      hp,
    };
  }

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    const input = currentInput();
    problems = validateReport(input);
    if (problems.length > 0) return;
    if (!config.report?.url) return;
    phase = 'submitting';
    submitError = '';
    const token = newToken();
    const result = await submitReport(config.report.url, {
      ...buildReportPayload(input),
      trackToken: token,
    });
    if (result.ok) {
      trackLink = trackUrl(token, 'report');
      phase = 'done';
    } else {
      phase = 'form';
      submitError = result.error ?? 'Something went wrong. Please try again.';
    }
  }
</script>

{#if open}
  <Modal
    close={fullClose}
    labelledby="report-title"
    class="civic-dialog"
    style="--modal-z: 2500; --modal-backdrop-bg: rgba(0, 0, 0, 0.5); --modal-shadow: 0 1.5rem 4rem rgba(0, 0, 0, 0.3); --modal-padding: 1.6rem 1.6rem 1.4rem"
  >
    {#if phase === 'done'}
      <h2 id="report-title">Report sent</h2>
      <p class="lead">
        Thanks. Your report goes to the City of Burton public-works queue for triage.
        This is a report line, not an emergency line: for anything dangerous right now,
        call 911 or the DPW at (810) 742-9230.
      </p>
      <TrackLinkPanel {trackLink} kind="report" />
      <button class="civic-primary-btn" onclick={fullClose}>Done</button>
    {:else}
      <h2 id="report-title">Report an issue</h2>
      <p class="lead">
        Spotted a pothole, damaged sign, drainage problem, or missed trash pickup? Mark the
        spot or enter an address and tell us about it. Reports go to city staff and are not
        published.
      </p>

      <form class="civic-form" onsubmit={submit}>
        <div class="pin" class:set={hasPin}>
          {#if hasPin}
            <span>
              Pin set at {ui.report.lat?.toFixed(5)}, {ui.report.lng?.toFixed(5)}
            </span>
            <button type="button" class="linkish" onclick={startReportPin}>Change spot</button>
          {:else}
            <span>Where is it?</span>
            <button type="button" class="linkish" onclick={startReportPin}>
              Tap the map to drop a pin
            </button>
          {/if}
        </div>

        <label>
          Address <span class="opt">(or drop a pin above)</span>
          <input
            type="text"
            bind:value={address}
            oninput={() => (addressAutoFilled = false)}
            maxlength="255"
            placeholder="e.g. 3025 S Center Rd"
            autocomplete="street-address"
          />
        </label>
        {#if addressLookupBusy}
          <p class="lookup-hint">Looking up the nearest address...</p>
        {:else if addressAutoFilled}
          <p class="lookup-hint">Nearest address filled in from your pin. Edit it if it's not quite right.</p>
        {/if}

        <label>
          What kind of issue?
          <select bind:value={category} required>
            {#each REPORT_CATEGORIES as c (c)}
              <option value={c}>{c}</option>
            {/each}
          </select>
        </label>

        <label>
          What's going on? <span class="opt">(optional but helpful)</span>
          <textarea bind:value={description} rows="3" maxlength="2000"></textarea>
        </label>

        <label>
          Photo <span class="opt">(optional, resized on your device before upload)</span>
          <input type="file" accept="image/*" capture="environment" onchange={onPhotoChange} />
        </label>
        {#if photoName}
          <p class="photo-ok">Attached: {photoName}</p>
        {/if}
        {#if photoError}
          <p class="problems">{photoError}</p>
        {/if}

        <fieldset>
          <legend>Contact (optional)</legend>
          <p class="privacy">
            Only if you want a follow-up. Used by city staff only, never published. See our
            <a href="https://explore.burtonmi.gov/privacy.html" target="_blank" rel="noopener noreferrer"
              >privacy policy</a
            >.
          </p>
          <label>
            Your name <span class="opt">(optional)</span>
            <input type="text" bind:value={contactName} maxlength="255" autocomplete="name" />
          </label>
          <label>
            Phone or email <span class="opt">(optional)</span>
            <input type="text" bind:value={contactInfo} maxlength="255" autocomplete="email" />
          </label>
        </fieldset>

        <!-- Honeypot: visually hidden; bots that fill it are rejected server-side. -->
        <div class="hp" aria-hidden="true">
          <label>
            Leave this field empty
            <input type="text" bind:value={hp} tabindex="-1" autocomplete="off" />
          </label>
        </div>

        {#if problems.length > 0}
          <ul class="problems" role="alert">
            {#each problems as p (p)}
              <li>{p}</li>
            {/each}
          </ul>
        {/if}
        {#if submitError}
          <p class="problems" role="alert">{submitError}</p>
        {/if}

        <button class="civic-primary-btn" type="submit" disabled={phase === 'submitting'}>
          {phase === 'submitting' ? 'Sending...' : 'Send report'}
        </button>
      </form>
    {/if}
  </Modal>
{/if}

<style>
  h2 {
    margin: 0 1.5rem 0.3rem 0;
    font-family: var(--font-head, sans-serif);
    font-weight: 700;
    font-size: 1.35rem;
    color: var(--civic-blue, #2c57a0);
  }
  .lead {
    margin: 0 0 1rem;
    font-size: 0.92rem;
    color: var(--pub-muted, #5c5c5c);
  }
  .pin {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    border: 1px dashed var(--pub-border, #d8dde4);
    border-radius: var(--pub-radius, 12px);
    padding: 0.55rem 0.8rem;
    font-size: 0.88rem;
    font-weight: 600;
  }
  .pin.set {
    border-style: solid;
    border-color: var(--civic-blue, #2c57a0);
  }
  .linkish {
    border: none;
    background: none;
    padding: 0;
    font-family: var(--font-body, sans-serif);
    font-size: 0.85rem;
    color: var(--civic-blue-link);
    text-decoration: underline;
    cursor: pointer;
    white-space: nowrap;
  }
  .linkish:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: var(--pub-radius-sm, 8px);
  }
  .lookup-hint {
    margin: -0.45rem 0 0;
    font-size: 0.78rem;
    font-weight: 400;
    color: var(--pub-muted, #5c5c5c);
  }
  .photo-ok {
    margin: -0.35rem 0 0;
    font-size: 0.8rem;
    color: var(--pub-success);
  }
</style>
