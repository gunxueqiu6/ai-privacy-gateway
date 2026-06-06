import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://gunxueqiu6.github.io',
  base: '/ai-privacy-gateway',
  output: 'static',
  build: {
    assets: 'assets',
  },
});
