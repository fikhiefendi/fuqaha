import { getCollection, type CollectionEntry } from 'astro:content';
import type { ImageMetadata } from 'astro';
import { LOCALES, pick, useT, type Lang } from '../i18n/ui';
import { href } from './url';
import { scholarSummary } from './scholars';
import { backdrop, photo, type Photo, type PhotoId } from './images';

export type LocalPost = {
  slug: string;
  entry: CollectionEntry<'posts'>;
  /** Language the shown text is actually in. */
  lang: Lang;
  /** True when the requested language was missing and another one is shown. */
  fallback: boolean;
};

/** One entry per post slug, in the requested language when a translation exists. */
export async function getPosts(lang: Lang): Promise<LocalPost[]> {
  const all = await getCollection('posts', ({ data }) => !data.draft);
  const bySlug = new Map<string, Map<Lang, CollectionEntry<'posts'>>>();
  for (const entry of all) {
    const [l, ...rest] = entry.id.split('/');
    const slug = rest.join('/');
    if (!bySlug.has(slug)) bySlug.set(slug, new Map());
    bySlug.get(slug)!.set(l as Lang, entry);
  }
  const order: Lang[] = [lang, 'tr', ...LOCALES];
  return [...bySlug]
    .map(([slug, versions]) => {
      const shown = order.find((l) => versions.has(l))!;
      return { slug, entry: versions.get(shown)!, lang: shown, fallback: shown !== lang };
    })
    .sort((a, b) => b.entry.data.date.valueOf() - a.entry.data.date.valueOf());
}

/** Items for the home-page slider: newest posts, jurists and works together. */
export type FeatureItem = {
  kind: 'post' | 'scholar' | 'work';
  kicker: string;
  title: string;
  titleLang: Lang;
  summary?: string;
  date: Date;
  href: string;
  seed: string;
  image?: ImageMetadata;
  imageAlt?: string;
  /** Registered photo shown behind the slide, with its caption. */
  photo?: Photo;
  label?: string;
};

/** The image to show for a post: its own cover, else its registered photo. */
export function postImage(entry: CollectionEntry<'posts'>, lang: Lang) {
  if (entry.data.cover) return { src: entry.data.cover, alt: entry.data.coverAlt ?? '' };
  if (!entry.data.photo) return undefined;
  const p = photo(entry.data.photo as PhotoId);
  return { src: p.src, alt: p.caption[lang], photo: p };
}

export async function getFeatured(lang: Lang, limit = 5): Promise<FeatureItem[]> {
  const t = useT(lang);
  const posts = (await getPosts(lang))
    .filter((p) => p.entry.data.featured)
    .map<FeatureItem>((p) => ({
      kind: 'post',
      kicker: t('kind.post'),
      title: p.entry.data.title,
      titleLang: p.lang,
      summary: p.entry.data.summary,
      date: p.entry.data.date,
      href: href(lang, `posts/${p.slug}/`),
      seed: p.slug,
      image: postImage(p.entry, lang)?.src,
      imageAlt: postImage(p.entry, lang)?.alt,
      photo: postImage(p.entry, lang)?.photo,
    }));
  const scholars = (await getCollection('scholars', ({ data }) => data.featured)).map<FeatureItem>((s) => ({
    kind: 'scholar',
    kicker: t('kind.scholar'),
    title: s.data.name[lang],
    titleLang: lang,
    summary: scholarSummary(s, lang),
    date: s.data.addedAt,
    href: href(lang, `scholars/${s.id}/`),
    seed: s.id,
    label: s.data.name.ar,
    photo: backdrop(s.id),
  }));
  const works = (await getCollection('works', ({ data }) => (data as { featured?: boolean }).featured === true)).map<FeatureItem>((w) => ({
    kind: 'work',
    kicker: t('kind.work'),
    title: w.data.title,
    titleLang: (w.data.language as Lang) ?? lang,
    summary: pick(w.data.titleTranslation, lang) ?? w.data.authors.join(', '),
    date: w.data.addedAt,
    href: href(lang, `bibliography/${w.id}/`),
    seed: w.id,
    photo: backdrop(w.id),
  }));
  // Alternate the newest essays with featured jurists and works.
  const lists = [posts, scholars, works].map((l) => l.sort((a, b) => b.date.valueOf() - a.date.valueOf()));
  const out: FeatureItem[] = [];
  for (let i = 0; out.length < limit && lists.some((l) => l[i]); i++) {
    for (const l of lists) if (l[i] && out.length < limit) out.push(l[i]);
  }
  return out;
}

export function formatDate(date: Date, lang: Lang) {
  const locale = { tr: 'tr-TR', en: 'en-GB', ar: 'ar' }[lang];
  return new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'long', year: 'numeric' }).format(date);
}
