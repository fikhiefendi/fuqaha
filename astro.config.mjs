import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// GitHub Pages: https://fikhiefendi.github.io/<repo>/
// BASE_PATH is set by the deploy workflow; locally the site runs at "/".
export default defineConfig({
  site: 'https://fikhiefendi.github.io',
  base: process.env.BASE_PATH ?? '/',
  trailingSlash: 'always',
  server: { port: Number(process.env.PORT) || 4321 },
  integrations: [
    sitemap({
      i18n: { defaultLocale: 'tr', locales: { tr: 'tr-TR', en: 'en-GB', ar: 'ar' } },
      filter: (page) => !/\/(search|404)\//.test(page),
    }),
  ],
});
