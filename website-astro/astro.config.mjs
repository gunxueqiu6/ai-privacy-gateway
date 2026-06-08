import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://privacygw.pages.dev',
  base: '/',
  integrations: [sitemap()],
});
