<script lang="ts">
  import { dataFetch } from '../remote';
  import { loadAddressPoints } from '../reverseGeocode';
  import {
    findPrecinct,
    matchAddress,
    suggestAddresses,
    type AddressRow,
    type PrecinctFeature,
  } from './precinctFinder';

  const MVIC = 'https://mvic.sos.state.mi.us/';

  type Outcome =
    | { kind: 'idle' }
    | { kind: 'error' }
    | { kind: 'found'; address: string; name: string }
    | { kind: 'outside'; address: string }
    | { kind: 'nomatch'; suggestions: AddressRow[] };

  let query = $state('');
  let busy = $state(false);
  let outcome = $state<Outcome>({ kind: 'idle' });
  let precincts: PrecinctFeature[] | null = null;

  async function loadPrecincts(): Promise<PrecinctFeature[]> {
    if (precincts) return precincts;
    const res = await dataFetch('precincts.geojson');
    if (!res.ok) throw new Error('precincts');
    const json = (await res.json()) as { features?: PrecinctFeature[] };
    precincts = Array.isArray(json.features) ? json.features : [];
    return precincts;
  }

  async function lookup(text: string): Promise<void> {
    if (text.trim() === '') return;
    busy = true;
    try {
      const [rows, feats] = await Promise.all([
        loadAddressPoints('address-points.json'),
        loadPrecincts(),
      ]);
      if (rows.length === 0 || feats.length === 0) {
        outcome = { kind: 'error' };
        return;
      }
      const hit = matchAddress(text, rows);
      if (!hit) {
        outcome = { kind: 'nomatch', suggestions: suggestAddresses(text, rows, 5) };
        return;
      }
      const p = findPrecinct(hit.lat, hit.lng, feats);
      outcome = p
        ? { kind: 'found', address: hit.address, name: p.name }
        : { kind: 'outside', address: hit.address };
    } catch {
      outcome = { kind: 'error' };
    } finally {
      busy = false;
    }
  }

  function pick(address: string): void {
    query = address;
    void lookup(address);
  }
</script>

<section class="finder" aria-labelledby="precinct-finder-title">
  <h3 id="precinct-finder-title">Look up your precinct</h3>
  <form
    onsubmit={(e) => {
      e.preventDefault();
      void lookup(query);
    }}
  >
    <label for="precinct-address">Your Burton street address</label>
    <div class="row">
      <input
        id="precinct-address"
        type="text"
        placeholder="e.g. 4303 S Center Rd"
        autocomplete="street-address"
        bind:value={query}
      />
      <button type="submit" disabled={busy || query.trim() === ''}>
        {busy ? 'Looking…' : 'Find precinct'}
      </button>
    </div>
  </form>

  <div class="result" aria-live="polite">
    {#if outcome.kind === 'found'}
      <p class="ok">
        <strong>You are in {outcome.name}.</strong>
        <span class="addr">({outcome.address})</span>
      </p>
      <p>
        <a href={MVIC} target="_blank" rel="noopener noreferrer"
          >Find your polling place and sample ballot on the Michigan Voter Information Center</a
        >
      </p>
    {:else if outcome.kind === 'outside'}
      <p class="warn">
        <strong>Not found:</strong> {outcome.address} is not inside any City of Burton precinct.
      </p>
      <p>
        <a href={MVIC} target="_blank" rel="noopener noreferrer"
          >Check your voting information on the Michigan Voter Information Center</a
        >
      </p>
    {:else if outcome.kind === 'nomatch'}
      <p class="warn"><strong>No exact match</strong> for &ldquo;{query}&rdquo;.</p>
      {#if outcome.suggestions.length > 0}
        <p>Did you mean:</p>
        <ul class="suggest">
          {#each outcome.suggestions as s (s.address)}
            <li><button type="button" onclick={() => pick(s.address)}>{s.address}</button></li>
          {/each}
        </ul>
      {/if}
      <p>
        <a href={MVIC} target="_blank" rel="noopener noreferrer"
          >Look up your voting information on the Michigan Voter Information Center</a
        >
      </p>
    {:else if outcome.kind === 'error'}
      <p class="warn"><strong>The lookup is unavailable right now.</strong></p>
      <p>
        <a href={MVIC} target="_blank" rel="noopener noreferrer"
          >Use the Michigan Voter Information Center</a
        >
      </p>
    {/if}
  </div>
  <p class="note">
    Your address is matched on your device and is not sent anywhere. For your polling place, early
    voting sites, and election dates, always use the official Michigan Voter Information Center.
  </p>
</section>

<style>
  .finder {
    max-width: 640px;
    margin: 0 0 1.4rem;
    padding: 1rem 1.1rem;
    background: var(--pub-surface, #fff);
    border: 1px solid var(--pub-border, #d8dde4);
    border-left: 4px solid var(--civic-blue, #2c57a0);
    border-radius: var(--pub-radius, 10px);
  }
  h3 {
    margin: 0 0 0.6rem;
    font-family: var(--font-head, sans-serif);
    color: var(--civic-blue, #2c57a0);
    font-size: 1.05rem;
  }
  label {
    display: block;
    font-weight: 600;
    font-size: 0.9rem;
    margin-bottom: 0.3rem;
  }
  .row {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  input {
    flex: 1 1 14rem;
    min-width: 0;
    box-sizing: border-box;
    padding: 0.65rem 0.85rem;
    font-size: 1rem;
    font-family: var(--font-body, Inter, sans-serif);
    border: 2px solid var(--pub-border, #d8dde4);
    border-radius: var(--pub-radius, 10px);
  }
  input:focus-visible,
  button:focus-visible,
  a:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  input:focus-visible {
    border-color: var(--civic-blue, #2c57a0);
  }
  button[type='submit'] {
    border: none;
    background: var(--civic-accent-bg, #2c57a0);
    color: #fff;
    border-radius: var(--pub-btn-radius, 12px);
    padding: 0.6rem 1.2rem;
    font-family: var(--font-body, sans-serif);
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
  }
  button[type='submit']:disabled {
    opacity: 0.6;
    cursor: default;
  }
  .result {
    margin-top: 0.8rem;
    line-height: 1.5;
  }
  .result p {
    margin: 0.4rem 0;
  }
  .ok::before {
    content: 'Result: ';
    font-weight: 700;
  }
  .warn::before {
    content: 'Notice: ';
    font-weight: 700;
  }
  .addr {
    color: var(--pub-muted, #5c5c5c);
    font-size: 0.9rem;
  }
  .suggest {
    list-style: none;
    margin: 0.3rem 0;
    padding: 0;
  }
  .suggest button {
    margin: 0.15rem 0;
    border: 1px solid var(--civic-blue, #2c57a0);
    background: var(--pub-surface, #fff);
    color: var(--civic-blue, #2c57a0);
    border-radius: var(--pub-btn-radius, 12px);
    padding: 0.35rem 0.9rem;
    font-family: var(--font-body, sans-serif);
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
  }
  a {
    color: var(--civic-blue-link, #386fc5);
  }
  .note {
    margin: 0.8rem 0 0;
    font-size: 0.78rem;
    color: var(--pub-muted, #5c5c5c);
    line-height: 1.4;
  }
</style>
