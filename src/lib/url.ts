import { LOCALES, type Lang } from '../i18n/ui';

// Prefixes internal links with the base path (the repo name on GitHub Pages).
export function url(path = ''): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  return `${base}/${path.replace(/^\//, '')}`;
}

/** Link to a page in a given language, e.g. href('ar', 'posts/') → /ar/posts/ */
export function href(lang: Lang, path = ''): string {
  return url(`${lang}/${path.replace(/^\//, '')}`);
}

/** The same page in another language. */
export function switchLang(pathname: string, to: Lang): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  const rest = pathname.slice(base.length).replace(/^\/(tr|en|ar)(?=\/|$)/, '');
  return url(`${to}${rest || '/'}`);
}

export function langFromParam(param: string | undefined): Lang {
  return (LOCALES as readonly string[]).includes(param ?? '') ? (param as Lang) : 'tr';
}

// Hijri year → century (1–100 AH is the 1st century).
export function century(hijri: number): number {
  return Math.ceil(hijri / 100);
}
