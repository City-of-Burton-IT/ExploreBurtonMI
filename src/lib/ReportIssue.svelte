<script lang="ts">
  import type { AppConfig } from './types';
  import { ui, closeReport, startReportPin, registerOverlay } from './store.svelte';
  import {
    REPORT_CATEGORIES,
    type ReportCategory,
    type ReportInput,
    PHOTO_BASE64_MAX,
    buildReportPayload,
    validateReport,
    submitReport,
  } from './report';

  // "Report an issue" (#14): pin + optional photo/notes -> the private DPW
  // triage queue. Never published; this is a report, not an emergency line.
  // Modal mechanics mirror SuggestEdit.svelte / WelcomeModal.svelte.

  let { config }: { config: AppConfig } = $props();

  const open = $derived(ui.report.open && !!config.report?.url);
  const hasPin = $derived(ui.report.lat != null && ui.report.lng != null);

  let category = $state<ReportCategory | ''>('Pothole');
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
  }

  function fullClose() {
    closeReport();
  }

  // Android hardware back: leave pin mode or close the modal.
  $effect(() => {
    if (open) return registerOverlay(fullClose);
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
    const result = await submitReport(config.report.url, buildReportPayload(input));
    if (result.ok) {
      phase = 'done';
    } else {
      phase = 'form';
      submitError = result.error ?? 'Something went wrong. Please try again.';
    }
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') fullClose();
  }
</script>

<svelte:window onkeydown={open ? onKeydown : undefined} />

{#if open}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    class="backdrop"
    role="presentation"
    onclick={(e) => {
      if (e.target === e.currentTarget) fullClose();
    }}
  >
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="report-title" tabindex="-1">
      <button class="close" onclick={fullClose} aria-label="Close">&times;</button>

      {#if phase === 'done'}
        <h2 id="report-title">Report sent</h2>
        <p class="lead">
          Thanks. Your report goes to the City of Burton public-works queue for triage.
          This is a report line, not an emergency line: for anything dangerous right now,
          call 911 or the DPW at (810) 742-9230.
        </p>
        <button class="primary" onclick={fullClose}>Done</button>
      {:else}
        <h2 id="report-title">Report an issue</h2>
        <p class="lead">
          Spotted a pothole, damaged sign, drainage problem, or streetlight out? Mark the
          spot and tell us about it. Reports go to city staff and are not published.
        </p>

        <form onsubmit={submit}>
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

          <button class="primary" type="submit" disabled={phase === 'submitting'}>
            {phase === 'submitting' ? 'Sending...' : 'Send report'}
          </button>
        </form>
      {/if}
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 2500;
    background: rgba(0, 0, 0, 0.5);
    display: grid;
    place-items: center;
    padding: 1.2rem;
  }
  .modal {
    position: relative;
    width: 100%;
    max-width: 480px;
    max-height: calc(100% - 2rem);
    overflow-y: auto;
    background: var(--pub-surface);
    border-radius: var(--pub-radius-lg, 16px);
    box-shadow: 0 1.5rem 4rem rgba(0, 0, 0, 0.3);
    padding: 1.6rem 1.6rem 1.4rem;
    padding-bottom: calc(
      1.4rem + var(--safe-area-inset-bottom, env(safe-area-inset-bottom, 0px))
    );
  }
  .close {
    position: absolute;
    top: 0.6rem;
    right: 0.7rem;
    border: none;
    background: none;
    font-size: 1.7rem;
    line-height: 1;
    color: var(--pub-muted, #5c5c5c);
    cursor: pointer;
  }
  .close:hover {
    color: var(--civic-blue, #2c57a0);
  }
  .close:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: var(--pub-radius-sm, 8px);
  }
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
  form {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
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
  label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--pub-ink, #2c2c2c);
  }
  .opt {
    font-weight: 400;
    color: var(--pub-muted, #5c5c5c);
  }
  input,
  select,
  textarea {
    font: inherit;
    font-weight: 400;
    color: var(--pub-ink, #2c2c2c);
    background: var(--pub-surface);
    border: 1px solid var(--pub-border, #d8dde4);
    border-radius: var(--pub-radius-sm, 8px);
    padding: 0.5rem 0.6rem;
    min-height: 44px;
  }
  textarea {
    resize: vertical;
    min-height: 70px;
  }
  input:focus-visible,
  select:focus-visible,
  textarea:focus-visible {
    outline: none;
    border-color: var(--civic-blue, #2c57a0);
    box-shadow: var(--pub-focus-ring);
  }
  fieldset {
    margin: 0.2rem 0 0;
    border: 1px solid var(--pub-border, #d8dde4);
    border-radius: var(--pub-radius, 12px);
    padding: 0.6rem 0.8rem 0.8rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  legend {
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--civic-blue-deep, #1e437e);
    padding: 0 0.3rem;
  }
  .privacy {
    margin: 0;
    font-size: 0.78rem;
    font-weight: 400;
    color: var(--pub-muted, #5c5c5c);
  }
  .privacy a {
    color: var(--civic-blue-link);
  }
  .photo-ok {
    margin: -0.35rem 0 0;
    font-size: 0.8rem;
    color: var(--pub-success);
  }
  .hp {
    position: absolute;
    left: -9999px;
    width: 1px;
    height: 1px;
    overflow: hidden;
  }
  .problems {
    margin: 0;
    padding: 0.55rem 0.8rem 0.55rem 1.6rem;
    color: var(--pub-error);
    border: 1px solid var(--pub-error);
    border-radius: var(--pub-radius-sm, 8px);
    font-size: 0.85rem;
  }
  p.problems {
    padding-left: 0.8rem;
  }
  .primary {
    margin-top: 0.3rem;
    width: 100%;
    border: none;
    background: var(--civic-accent-bg);
    color: #fff;
    border-radius: 999px;
    padding: 0.65rem 1rem;
    font-family: var(--font-body, sans-serif);
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
  }
  .primary:hover {
    background: var(--civic-accent-bg-hover);
  }
  .primary:disabled {
    opacity: 0.6;
    cursor: default;
  }
  .primary:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
</style>
