<script lang="ts">
  import { tryUnlock } from './comingSoon';

  let phrase = $state('');
  let error = $state(false);

  function submit(e: Event) {
    e.preventDefault();
    if (tryUnlock(phrase)) {
      // Unlocked: reload so the gate now passes and the real app mounts.
      window.location.reload();
    } else {
      error = true;
    }
  }
</script>

<main class="cs">
  <div class="card">
    <img class="seal" src="/burton-seal.png" alt="City of Burton seal" />
    <p class="eyebrow">Explore Burton</p>
    <h1>Coming soon</h1>
    <p class="lead">
      We're putting the finishing touches on the City of Burton's new interactive
      map and community dashboards. Please check back shortly.
    </p>

    <form class="unlock" onsubmit={submit}>
      <label for="cs-phrase">Have early access?</label>
      <div class="row">
        <input
          id="cs-phrase"
          type="text"
          autocomplete="off"
          autocapitalize="none"
          spellcheck="false"
          placeholder="Enter your phrase"
          bind:value={phrase}
          oninput={() => (error = false)}
          aria-invalid={error}
        />
        <button type="submit">Enter</button>
      </div>
      {#if error}
        <p class="err" role="alert">That phrase didn't match. Try again.</p>
      {/if}
    </form>

    <p class="foot">City of Burton, Michigan</p>
  </div>
</main>

<style>
  .cs {
    min-height: 100vh;
    min-height: 100dvh;
    display: grid;
    place-items: center;
    padding: 1.5rem;
    background:
      radial-gradient(circle at 50% -10%, var(--civic-blue-soft), transparent 60%),
      #f6f8fc;
  }
  .card {
    background: var(--pub-surface);
    border-radius: var(--pub-radius-lg, 16px);
    box-shadow: 0 1rem 3rem rgba(0, 0, 0, 0.12);
    border-top: 6px solid var(--civic-green);
    max-width: 460px;
    width: 100%;
    padding: 2.2rem 2rem 1.8rem;
    text-align: center;
  }
  .seal {
    width: 84px;
    height: 84px;
    object-fit: contain;
    margin-bottom: 0.6rem;
  }
  .eyebrow {
    margin: 0;
    font-family: var(--font-head);
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    font-size: 0.8rem;
    color: var(--civic-green-deep);
  }
  h1 {
    margin: 0.1rem 0 0.7rem;
    font-family: var(--font-head);
    font-weight: 700;
    font-size: 2rem;
    color: var(--civic-blue);
  }
  .lead {
    margin: 0 0 1.4rem;
    line-height: 1.6;
    color: var(--pub-ink);
  }
  .unlock {
    text-align: left;
    border-top: 2px dashed var(--civic-green);
    padding-top: 1.1rem;
  }
  .unlock label {
    display: block;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--pub-muted);
    margin-bottom: 0.4rem;
  }
  .row {
    display: flex;
    gap: 0.5rem;
  }
  input {
    flex: 1;
    min-width: 0;
    padding: 0.55rem 0.7rem;
    border: 1px solid var(--pub-border);
    border-radius: var(--pub-radius-sm);
    font-family: var(--font-body);
    font-size: 1rem;
    color: var(--pub-ink);
  }
  input:focus-visible {
    outline: none;
    border-color: var(--civic-blue);
    box-shadow: var(--pub-focus-ring);
  }
  button {
    border: none;
    background: var(--civic-accent-bg);
    color: #fff;
    border-radius: var(--pub-radius-sm);
    padding: 0 1.1rem;
    font-family: var(--font-body);
    font-weight: 700;
    font-size: 0.95rem;
    cursor: pointer;
    transition: background var(--motion-duration);
  }
  button:hover {
    background: var(--civic-accent-bg-hover);
  }
  button:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .err {
    margin: 0.5rem 0 0;
    font-size: 0.85rem;
    color: #b32020;
  }
  .foot {
    margin: 1.5rem 0 0;
    font-size: 0.8rem;
    color: var(--pub-muted);
  }
</style>
