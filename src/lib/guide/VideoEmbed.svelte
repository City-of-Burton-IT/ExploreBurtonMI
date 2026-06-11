<script lang="ts">
  // Privacy-respecting click-to-load video. Nothing is requested from the provider
  // (and no third-party cookie is set) until the visitor presses play -- preserving
  // the site's cookieless posture. The branded poster avoids a third-party thumbnail.
  let {
    src,
    title = 'Video',
    provider = '',
  }: { src: string; title?: string; provider?: string } = $props();

  let playing = $state(false);
</script>

<div class="video">
  {#if playing}
    <div class="video-frame">
      <iframe
        {src}
        {title}
        allow="fullscreen; autoplay; encrypted-media"
        allowfullscreen
        loading="lazy"
        referrerpolicy="no-referrer"
      ></iframe>
    </div>
  {:else}
    <button class="video-poster" type="button" onclick={() => (playing = true)} aria-label="Play {title}">
      <span class="play" aria-hidden="true"></span>
      <span class="cta">{title}</span>
    </button>
    {#if provider}
      <p class="video-note">
        Loads from {provider} when you press play (it may set its own cookies).
      </p>
    {/if}
  {/if}
</div>

<style>
  .video {
    margin: 0.4rem 0 0.2rem;
  }
  .video-frame {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    border-radius: var(--pub-radius, 12px);
    overflow: hidden;
    background: #000;
  }
  .video-frame iframe {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: 0;
  }
  .video-poster {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    border: none;
    border-radius: var(--pub-radius, 12px);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.9rem;
    color: #fff;
    background:
      radial-gradient(circle at 50% 38%, var(--civic-blue, #2c57a0), var(--civic-blue-deep, #1e437e));
  }
  .video-poster:focus-visible {
    outline: none;
    box-shadow: var(--pub-focus-ring);
  }
  .play {
    width: 4.2rem;
    height: 4.2rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.18);
    display: grid;
    place-items: center;
    transition: background 0.15s, transform 0.15s;
  }
  .play::before {
    content: '';
    width: 0;
    height: 0;
    border-style: solid;
    border-width: 0.85rem 0 0.85rem 1.4rem;
    border-color: transparent transparent transparent #fff;
    margin-left: 0.35rem;
  }
  .video-poster:hover .play {
    background: rgba(255, 255, 255, 0.3);
    transform: scale(1.05);
  }
  .cta {
    font-family: var(--font-head, sans-serif);
    font-weight: 700;
    font-size: 1.05rem;
  }
  .video-note {
    margin: 0.5rem 0 0;
    font-size: 0.78rem;
    color: var(--pub-muted, #5c5c5c);
  }
</style>
