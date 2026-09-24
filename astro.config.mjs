import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import { readdirSync, readFileSync } from 'node:fs';

// Theses added by the harvester (tools/tezci) have a Turkish page only; their en/ar
// addresses are redirects and are left out of the sitemap.
const WORKS = './src/content/works';
const AUTO = new Set(
  readdirSync(WORKS)
    .filter((f) => f.endsWith('.yaml') && /^origin: otomatik$/m.test(readFileSync(`${WORKS}/${f}`, 'utf8')))
    .map((f) => f.slice(0, -5)),
);
const isRedirect = (page) => {
  const m = /\/(en|ar)\/bibliography\/([^/]+)\/$/.exec(page);
  return !!m && AUTO.has(m[2]);
};

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
      filter: (page) => !/\/(search|404)\//.test(page) && !isRedirect(page),
    }),
  ],
});
