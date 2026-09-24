import { defineConfig } from 'astro/config';

// GitHub Pages: https://fikhiefendi.github.io/<repo>/
// BASE_PATH is set by the deploy workflow; locally the site runs at "/".
export default defineConfig({
  site: 'https://fikhiefendi.github.io',
  base: process.env.BASE_PATH ?? '/',
  trailingSlash: 'always',
});
