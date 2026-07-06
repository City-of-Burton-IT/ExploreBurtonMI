<script lang="ts">
  import type { AppConfig } from './types';
  import { ui, closeSuggest } from './store.svelte';
  import {
    CHANGE_TYPES,
    type ChangeType,
    type SuggestInput,
    buildPayload,
    validateSuggestion,
    submitSuggestion,
  } from './suggest';
  import { newToken, trackUrl } from './track';
  import Modal from './Modal.svelte';
  import TrackLinkPanel from './TrackLinkPanel.svelte';
  import './forms.css';

  // "Suggest an edit" / "Add my business" (#3). A resident files a listing
  // change request; it lands in the IT moderation queue (SharePoint) via the
  // intake flow. Nothing changes on the map until IT approves and the normal
  // data pipeline republishes. Modal mechanics (Escape, backdrop, Android back,
  // focus save/trap/restore) live in the shared <Modal>; this component keeps
  // only the field logic + its own dialog sizing.

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
  // The resident's tracking link, set on a successful submit (#status). The token
  // is generated client-side and sent with the payload so the intake flow can
  // store it on the row and email the same link.
  let trackLink = $state('');

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
      trackLink = '';
      // Move focus to the first field instead of Modal's default (its own close
      // button). Modal moves focus in via a queueMicrotask in its own $effect;
      // requestAnimationFrame guarantees this runs after that microtask drains,
      // so the select ends up focused rather than the close button.
      requestAnimationFrame(() => firstField?.focus());
    }
    prevOpen = open;
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
    const token = newToken();
    const result = await submitSuggestion(config.submit.url, {
      ...buildPayload(input),
      trackToken: token,
    });
    if (result.ok) {
      trackLink = trackUrl(token, 'listing');
      phase = 'done';
    } else {
      phase = 'form';
      submitError = result.error ?? 'Something went wrong. Please try again.';
    }
  }
</script>

{#if open}
  <Modal
    close={closeSuggest}
    labelledby="suggest-title"
    class="civic-dialog"
    style="--modal-z: 2500; --modal-backdrop-bg: rgba(0, 0, 0, 0.5); --modal-shadow: 0 1.5rem 4rem rgba(0, 0, 0, 0.3); --modal-padding: 1.6rem 1.6rem 1.4rem"
  >
    {#if phase === 'done'}
      <h2 id="suggest-title">Thanks, we got it</h2>
      <p class="lead">
        City of Burton IT reviews every request, usually within a few business days. If we need
        to confirm anything we'll use the contact you provided. Approved changes appear on the
        map after the next data update.
      </p>
      <TrackLinkPanel {trackLink} kind="request" />
      <button class="civic-primary-btn" onclick={closeSuggest}>Done</button>
    {:else}
      <h2 id="suggest-title">{place ? 'Suggest an edit' : 'Add a business'}</h2>
      <p class="lead">
        A real person in City of Burton IT reviews every request before anything changes on the
        map.
      </p>

      <form class="civic-form" onsubmit={submit}>
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
            Used only to confirm the request, never published. See our
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

        <button class="civic-primary-btn" type="submit" disabled={phase === 'submitting'}>
          {phase === 'submitting' ? 'Sending...' : 'Send request'}
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
</style>
