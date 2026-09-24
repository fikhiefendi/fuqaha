import { getCollection, type CollectionEntry } from 'astro:content';
import { pick, type Lang } from '../i18n/ui';
import { WORK_TYPES } from '../site.config';

export type Work = CollectionEntry<'works'>;

export async function getWorks(): Promise<Work[]> {
  return (await getCollection('works')).sort(
    (a, b) => (b.data.year ?? 0) - (a.data.year ?? 0) || a.data.authors[0].localeCompare(b.data.authors[0], 'tr'),
  );
}

/** "Kaya, Eyyüp Said" → "Eyyüp Said Kaya" */
export function displayName(name: string): string {
  const [last, first] = name.split(/,\s*/);
  return first ? `${first} ${last}` : name;
}

export function typeLabel(w: Work, lang: Lang): string {
  return pick(WORK_TYPES[w.data.type], lang) ?? w.data.type;
}

export function languageName(code: string, lang: Lang): string {
  try {
    return new Intl.DisplayNames([lang], { type: 'language' }).of(code) ?? code;
  } catch {
    return code;
  }
}

/** ISNAD-style reference (Turkish academic citation style). */
export function isnad(w: Work, lang: Lang): string {
  const d = w.data;
  const authors = d.authors.join(' - ');
  const kind = typeLabel(w, 'tr');
  const where = [d.city, d.university].filter(Boolean).join(': ');
  const year = d.year ?? (lang === 'tr' ? 'ts.' : 'n.d.');
  if (d.type.startsWith('tez')) return `${authors}. ${d.title}. ${where}, ${kind}, ${year}.`;
  return `${authors}. ${d.title}. ${[where, d.publisher].filter(Boolean).join(', ')}, ${year}.`;
}

export function bibtex(w: Work): string {
  const d = w.data;
  const kind = d.type === 'tez-doktora' ? 'phdthesis' : d.type === 'tez-yl' ? 'mastersthesis' : d.type === 'makale' ? 'article' : 'book';
  const f: [string, string | number | undefined][] = [
    ['author', d.authors.join(' and ')],
    ['title', d.title],
    ['school', d.university],
    ['address', d.city],
    ['year', d.year],
    ['journal', d.journal],
    ['publisher', d.publisher],
    ['language', d.language],
  ];
  const body = f
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `  ${k} = {${v}}`)
    .join(',\n');
  return `@${kind}{${w.id.replace(/-/g, '_')},\n${body}\n}`;
}
