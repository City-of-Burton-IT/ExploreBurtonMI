/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  test: {
    // filter.ts / templates.ts are pure logic - no DOM needed
    environment: 'node',
    include: ['test/**/*.test.ts'],
  },
})
