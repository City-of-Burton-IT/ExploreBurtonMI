<script lang="ts">
  import type { AppConfig } from './types';
  import { ui, closeSuggest, registerOverlay } from './store.svelte';
  import {
    CHANGE_TYPES,
    type ChangeType,
    type SuggestInput,
    buildPayload,
    validateSuggestion,
    submitSuggestion,
  } from './suggest';

  // "Suggest an edit" / "Add my business" (#3). A resident files a listing
  // change request; it lands in the IT moderation queue (SharePoint) via the
  // intake flow. Nothing changes on the map until IT approves and the normal
  // data pipeline republishes. Modal mechanics mirror WelcomeModal.svelte.

  let { config }: { config: AppConfig } = $props();

  const open = $derived(ui.suggest.open && !!config.submit?.url);
  const place = $derived(ui.suggest.place);

  let changeType = $state<ChangeType | ''>('');
  let businessName = $state('');
  let newName = $state('');
  let newAddress = $state('');
  let newPhone = $state('');
  let newWebsite = $state('');
  let newCategory = $state('');
  let newHours = $state('');
  let details = $state('');
  let contactName = $state('');
  let contactPhoneEmail = $state('');
  let contactRelationship = $state('');
  let hp = $state('');

  let phase = $state<'form' | 'submitting' | 'done'>('form');
  let problems = $state<string[]>([]);
  let submitError = $state('');

  // (Re)initialize whenever the modal opens for a new context.
  let prevOpen = false;
  $effect(() => {
    if (open && !prevOpen) {
      changeType = place ? 'Fix listing' : 'Add my business';
      businessName = place ? String(place.properties.name ?? '') : '';
      newName = newAddress = newPhone = newWebsite = newCategory = newHours = '';
      details = contactName = contactPhoneEmail = contactRelationship = hp = '';
      phase = 'form';
      problems = [];
      submitError = '';
      queueMicrotask(() => firstField?.focus());
    }
    prevOpen = open;
  });

  // Android hardware back closes the modal first (same chain as other overlays).
  $effect(() => {
    if (open) return registerOverlay(closeSuggest);
  });

  let firstField = $state<HTMLSelectElement>();

  const showEditFields = $derived(changeType === 'Fix listing');
  const showAddressField = $derived(
    changeType === 'Fix listing' || changeType === 'Moved' || changeType === 'Add my business',
  );
  const showAddFields = $derived(changeType === 'Add my business');
  const addressRequired = $derived(changeType === 'Moved' || changeType === 'Add my business');

  function currentInput(): SuggestInput {
    return {
      changeType,
      businessName,
      listingId: place?.id ?? '',
      newName,
      newAddress,
      newPhone,
      newWebsite,
      newCategory,
      newHours,
      details,
      contactName,
      contactPhoneEmail,
      contactRelationship,
      hp,
    };
  }

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    const input = currentInput();
    problems = validateSuggestion(input);
    if (problems.length > 0) return;
    if (!config.submit?.url) return;
    phase = 'submitting';
    submitError = '';
    const result = await submitSuggestion(config.submit.url, buildPayload(input));
    if (result.ok) {
      phase = 'done';
    } else {
      phase = 'form';
      submitError = result.error ?? 'Something went wrong. Please try again.';
    }
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') closeSuggest();
  }
</script>

<svelte:window onkeydown={open ? onKeydown : undefined} />

{#if open}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    class="backdrop"
    role="presentation"
    onclick={(e) => {
      if (e.target === e.currentTarget) closeSuggest();
    }}
  >
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="suggest-title" tabindex="-1">
      <button class="close" onclick={closeSuggest} aria-label="Close">&times;</button>

      {#if phase === 'done'}
        <h2 id="suggest-title">Thanks -- we got it</h2>
        <p class="lead">
          City of Burton IT reviews every request, usually within a few business days. If we need
          to confirm anything we'll use the contact you provided. Approved changes appear on the
          map after the next data update.
        </p>
        <button class="primary" onclick={closeSuggest}>Done</button>
      {:else}
        <h2 id="suggest-title">{place ? 'Suggest an edit' : 'Add a business'}</h2>
        <p class="lead">
          A real person in City of Burton IT reviews every request before anything changes on the
          map.
        </p>

        <form onsubmit={submit}>
          <label>
            What do you want to do?
            <select bind:this={firstField} bind:value={changeType} required>
              {#each CHANGE_TYPES as t (t)}
                <option value={t}>{t}</option>
              {/each}
            </select>
          </label>

          <label>
            Business name
            <input type="text" bind:value={businessName} required maxlength="255" />
          </label>

          {#if showEditFields}
            <label>
              Corrected name <span class="opt">(only if the name is wrong)</span>
              <input type="text" bind:value={newName} maxlength="255" />
            </label>
          {/if}

          {#if showAddressField}
            <label>
              {changeType === 'Moved' ? 'New address' : 'Address'}
              {#if !addressRequired}<span class="opt">(if it needs fixing)</span>{/if}
              <input type="text" bind:value={newAddress} required={addressRequired} maxlength="255" />
            </label>
          {/if}

          {#if showEditFields || showAddFields}
            <label>
              Phone <span class="opt">(optional)</span>
              <input type="text" bind:value={newPhone} maxlength="255" />
            </label>
            <label>
              Website <span class="opt">(optional)</span>
              <input type="text" bind:value={newWebsite} maxlength="255" />
            </label>
            <label>
              Hours <span class="opt">(optional)</span>
              <input type="text" bind:value={newHours} maxlength="2000" />
            </label>
          {/if}

          {#if showAddFields}
            <label>
              Type of business <span class="opt">(restaurant, retail, services...)</span>
              <input type="text" bind:value={newCategory} maxlength="255" />
            </label>
          {/if}

          <label>
            Anything else we should know? <span class="opt">(optional)</span>
            <textarea bind:value={details} rows="3" maxlength="2000"></textarea>
          </label>

          <fieldset>
            <legend>Contact for verification</legend>
            <p class="privacy">
              Used only to confirm the request -- never published. See our
              <a href="https://explore.burtonmi.gov/privacy.html" target="_blank" rel="noopener noreferrer"
                >privacy policy</a
              >.
            </p>
            <label>
              Your name
              <input type="text" bind:value={contactName} required maxlength="255" autocomplete="name" />
            </label>
            <label>
              Phone or email
              <input
                type="text"
                bind:value={contactPhoneEmail}
                required
                maxlength="255"
                autocomplete="email"
              />
            </label>
            <label>
              Relationship to the business <span class="opt">(owner, manager, employee...)</span>
              <input type="text" bind:value={contactRelationship} required maxlength="255" />
            </label>
          </fieldset>

          <!-- Honeypot: visually hidden, never filled by people. Bots filling it are
               rejected by the intake flow. aria-hidden keeps screen readers away. -->
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
            {phase === 'submitting' ? 'Sending...' : 'Send request'}
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
    /* Edge-to-edge (#30): keep the submit button clear of the gesture bar. */
    padding-bottom: calc(1.4rem + env(safe-area-inset-bottom, 0px));
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
