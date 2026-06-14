<script lang="ts">
  import {
    PUSH_TOPICS,
    isPushAvailable,
    loadPrefs,
    ensurePermission,
    setTopic,
  } from './push';

  // Opt-in push toggles (#64), shown in About. The whole section stays HIDDEN
  // until push is actually wired (native app + Firebase configured) -- so during
  // the "scaffold, Firebase later" phase residents see nothing misleading.

  let available = $state(false);
  let enabled = $state<Set<string>>(new Set());
  let denied = $state(false);
  let busy = $state('');

  $effect(() => {
    isPushAvailable().then((a) => {
      available = a;
      if (a) enabled = loadPrefs();
    });
  });

  async function toggle(id: string) {
    const turningOn = !enabled.has(id);
    busy = id;
    try {
      // Turning a topic on requires the OS notification permission first.
      if (turningOn) {
        const res = await ensurePermission();
        if (!res.granted) {
          denied = true;
          return;
        }
        denied = false;
      }
      if (await setTopic(id, turningOn)) {
        // reassign for reactivity
        const next = new Set(enabled);
        if (turningOn) next.add(id);
        else next.delete(id);
        enabled = next;
      }
    } finally {
      busy = '';
    }
  }
</script>

{#if available}
  <div class="push" role="group" aria-label="Notifications">
    <span class="push-label">Notifications</span>
    <p class="push-intro">
      Choose what the City can notify you about. You can change this any time, and in your
      device settings.
    </p>
    {#each PUSH_TOPICS as t (t.id)}
      <label class="topic">
        <input
          type="checkbox"
          checked={enabled.has(t.id)}
          disabled={busy === t.id}
          onchange={() => toggle(t.id)}
        />
        <span class="topic-text">
          <span class="topic-title">{t.label}</span>
          <span class="topic-desc">{t.description}</span>
        </span>
      </label>
    {/each}
    {#if denied}
      <p class="push-denied" role="alert">
        Notifications are turned off for this app. Enable them in your device settings to
        subscribe.
      </p>
    {/if}
  </div>
{/if}

<style>
  .push {
    margin: 0.2rem 0 0.9rem;
  }
  .push-label {
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--pub-ink);
  }
  .push-intro {
    margin: 0.2rem 0 0.5rem;
    font-size: 0.82rem;
    color: var(--pub-muted, #5c5c5c);
  }
  .topic {
    display: flex;
    align-items: flex-start;
    gap: 0.55rem;
    padding: 0.35rem 0;
    cursor: pointer;
  }
  .topic input {
    margin-top: 0.15rem;
    width: 1.1rem;
    height: 1.1rem;
    flex: none;
    accent-color: var(--civic-accent-bg);
  }
  .topic-text {
    display: flex;
    flex-direction: column;
    gap: 0.05rem;
  }
  .topic-title {
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--pub-ink);
  }
  .topic-desc {
    font-size: 0.78rem;
    color: var(--pub-muted, #5c5c5c);
    line-height: 1.3;
  }
  .push-denied {
    margin: 0.4rem 0 0;
    font-size: 0.8rem;
    color: var(--pub-error);
  }
  .topic input:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
    border-radius: 4px;
  }
</style>
