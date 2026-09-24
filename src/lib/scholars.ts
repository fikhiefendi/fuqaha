import { getCollection, type CollectionEntry } from 'astro:content';
import { pick, useT, type Lang } from '../i18n/ui';
import { century } from './url';
import { hm, hmLong } from './hijri';

export type Scholar = CollectionEntry<'scholars'>;

export async function getScholars(): Promise<Scholar[]> {
  return (await getCollection('scholars')).sort((a, b) => a.data.order - b.data.order);
}

/** Summary in the reader's language; in Arabic, the opening of the source text itself. */
export function scholarSummary(s: Scholar, lang: Lang): string {
  if (lang === 'ar') return arabicExcerpt(s, 220);
  return pick(s.data.summary, lang) ?? '';
}

export function arabicExcerpt(s: Scholar, max: number): string {
  const text = (s.body ?? '').replace(/\*\*[^*]+\*\*/, '').replace(/\s+/g, ' ').trim();
  return text.length > max ? text.slice(0, max).replace(/\s+\S*$/, '') + '…' : text;
}

/** Short life dates, e.g. "ö. 534/1139-40" */
export function lifeShort(s: Scholar, lang: Lang): string {
  const t = useT(lang);
  const d = s.data.death;
  if (!d.hijri) return '';
  return `${t('died')} ${d.approx ? t('scholar.approx') + ' ' : ''}${hm(d.hijri, d.month, d.day)}`;
}

/** Full date line for a birth or death record. */
export function dateLong(date: Scholar['data']['death'] | undefined, lang: Lang): string | undefined {
  if (!date?.hijri) return undefined;
  const t = useT(lang);
  const main = `${date.approx ? t('scholar.approx') + ' ' : ''}${hmLong(lang, date.hijri, date.month, date.day)}`;
  const alt = date.alt.length ? ` (${t('scholar.otherReports')}: ${date.alt.map((y) => hm(y)).join(', ')})` : '';
  return main + alt;
}

export function scholarCentury(s: Scholar): number | undefined {
  const y = s.data.death.hijri ?? (s.data.birth?.hijri ? s.data.birth.hijri + 60 : undefined);
  return y ? century(y) : undefined;
}

export function centuryLabel(c: number, lang: Lang): string {
  const t = useT(lang);
  if (lang === 'ar') {
    const ord = ['الأول', 'الثاني', 'الثالث', 'الرابع', 'الخامس', 'السادس', 'السابع', 'الثامن', 'التاسع', 'العاشر', 'الحادي عشر', 'الثاني عشر', 'الثالث عشر', 'الرابع عشر'];
    return `القرن ${ord[c - 1] ?? c}`;
  }
  if (lang === 'en') {
    const suf = c % 10 === 1 && c !== 11 ? 'st' : c % 10 === 2 && c !== 12 ? 'nd' : c % 10 === 3 && c !== 13 ? 'rd' : 'th';
    return `${c}${suf} c. AH`;
  }
  return `${c}${t('century.suffix')}`;
}
