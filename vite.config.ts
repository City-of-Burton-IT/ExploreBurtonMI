/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    svelte(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      includeAssets: [
        'favicon.svg',
        'apple-touch-icon.png',
        'pwa-192.png',
        'pwa-512.png',
        'pwa-maskable-512.png',
      ],
      manifest: {
        name: 'Explore Burton',
        short_name: 'Explore Burton',
        description:
          'Find businesses, government facilities, and services in the City of Burton, Michigan.',
        theme_color: '#2c57a0',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        categories: ['government', 'navigation', 'utilities'],
        icons: [
          { src: 'pwa-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: 'pwa-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: 'pwa-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Precache the app shell (hashed JS/CSS/HTML + small static assets). The
        // content hash busts each on deploy. Data + tiles are runtime-cached below.
        globPatterns: ['**/*.{js,css,html,svg,woff2}'],
        navigateFallback: '/index.html',
        runtimeCaching: [
          {
            // Committed data (data/boundary/overlays/info-*/guide/waste-schedule JSON):
            // prefer fresh so a pipeline re-run shows up, fall back to cache offline.
            urlPattern: ({ url }) =>
              /\/(data|boundary|precincts|school-districts|transit-routes|flood-zones|info-[^/]+|guide|waste-schedule|alerts|ops-status|freshness)\.(geo)?json$/.test(
                url.pathname,
              ),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'burton-data',
              networkTimeoutSeconds: 4,
              expiration: { maxEntries: 40, maxAgeSeconds: 60 * 60 * 24 * 30 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Basemap + reference tiles (Michigan imagery + Esri overlays): cache-first
            // with a cap so recently-viewed areas work offline -- never cache the world.
            urlPattern: ({ url }) =>
              /(imagery\.michigan\.gov|arcgisonline\.com)$/.test(url.hostname),
            handler: 'CacheFirst',
            options: {
              cacheName: 'burton-tiles',
              expiration: { maxEntries: 600, maxAgeSeconds: 60 * 60 * 24 * 14 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
      devOptions: { enabled: false },
    }),
  ],
  test: {
    // filter.ts / templates.ts are pure logic - no DOM needed
    environment: 'node',
    include: ['test/**/*.test.ts'],
  },
})
