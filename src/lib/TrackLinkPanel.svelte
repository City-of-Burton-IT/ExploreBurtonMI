<script lang="ts">
  // Post-submit "copy your tracking link" block, shared by SuggestEdit.svelte and
  // ReportIssue.svelte's `phase === 'done'` screen. Renders nothing until a link
  // exists (i.e. always mount unconditionally after a successful submit -- no
  // `{#if trackLink}` needed at the call site).
  let { trackLink, kind }: { trackLink: string; kind: 'request' | 'report' } = $props();

  let copied = $state(false);

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(trackLink);
      copied = true;
      setTimeout(() => (copied = false), 2500);
    } catch {
      /* clipboard blocked -> the link text is already on screen to copy by hand */
    }
  }
</script>

{#if trackLink}
  <div class="track">
    <p class="track-label">Track your {kind}:</p>
    <p class="track-link"><a href={trackLink}>{trackLink}</a></p>
    <button class="copy" type="button" onclick={copyLink}>
      {copied ? 'Copied' : 'Copy link'}
    </button>
    <p class="track-note">
      Save this link to check the status later. If you gave an email, we also sent it to you.
    </p>
  </div>
{/if}

<style>
  .track {
    margin: 0 0 1rem;
    padding: 0.8rem 0.9rem;
    background: var(--civic-accent-bg-soft, #eef3fb);
    border: 1px solid var(--pub-border, #d8dde4);
    border-radius: var(--pub-radius, 12px);
  }
  .track-label {
    margin: 0 0 0.3rem;
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--civic-blue-deep, #1e437e);
  }
  .track-link {
    margin: 0 0 0.5rem;
    font-size: 0.82rem;
    word-break: break-all;
  }
  .track-link a {
    color: var(--civic-blue-link);
  }
  .copy {
    border: 1px solid var(--civic-blue);
    background: var(--pub-surface);
    color: var(--civic-blue);
    border-radius: 999px;
    padding: 0.35rem 0.9rem;
    font: inherit;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
  }
  .copy:hover {
    background: var(--civic-accent-bg);
    color: #fff;
  }
  .copy:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .track-note {
    margin: 0.5rem 0 0;
    font-size: 0.78rem;
    color: var(--pub-muted, #5c5c5c);
  }
</style>
