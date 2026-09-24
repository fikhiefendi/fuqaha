import { getCollection, type CollectionEntry } from 'astro:content';
import { pick, type Lang } from '../i18n/ui';
import { WORK_TYPES } from '../site.config';
import { toBibtex, type Rec } from './cite';

export type Work = CollectionEntry<'works'>;

export async function getWorks(): Promise<Work[]> {
  return (await getCollection('works')).sort(
    (a, b) => (b.data.year ?? 0) - (a.data.year ?? 0) || a.data.authors[0].localeCompare(b.data.authors[0], 'tr'),
  );
}

// Former names of universities, so a university is counted once.
const RENAMED: Record<string, string> = {
  'Uludağ Üniversitesi': 'Bursa Uludağ Üniversitesi',
  'Osmangazi Üniversitesi': 'Eskişehir Osmangazi Üniversitesi',
  'Cumhuriyet Üniversitesi': 'Sivas Cumhuriyet Üniversitesi',
  'Bozok Üniversitesi': 'Yozgat Bozok Üniversitesi',
  'Hacı Bektaş Veli Üniversitesi': 'Nevşehir Hacı Bektaş Veli Üniversitesi',
  'Katip Çelebi Üniversitesi': 'İzmir Katip Çelebi Üniversitesi',
  "el-Câmiatü'l-Ürdüniyye Külliyyetü'd-Dirâsâti'l-Ulyâ": 'University of Jordan',
  "University of Jordan (Al-Jami'ah Al-Urdunia)": 'University of Jordan',
};

/** The university alone, without its institute, under its current name. */
export function universityName(u?: string): string {
  if (!u) return '';
  const name = u.split(/,\s*|\s+(?=(?:Sosyal Bilimler|Lisansüstü Eğitim|İslami İlimler) )/)[0].trim();
  return RENAMED[name] ?? RENAMED[u] ?? name;
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
  const kind = d.type === 'tez-doktora' ? 'Doktora Tezi' : d.type === 'tez-yl' ? 'Yüksek Lisans Tezi' : typeLabel(w, 'tr');
  const where = [d.city, d.university].filter(Boolean).join(': ');
  const year = d.year ?? (lang === 'tr' ? 'ts.' : 'n.d.');
  if (d.type.startsWith('tez')) return `${authors}. ${d.title}. ${where}, ${kind}, ${year}.`;
  return `${authors}. ${d.title}. ${[where, d.publisher].filter(Boolean).join(', ')}, ${year}.`;
}

/** Plain record for export formats. */
export function record(w: Work): Rec {
  const d = w.data;
  return {
    id: w.id,
    type: d.type,
    title: d.title,
    authors: d.authors,
    editors: d.editors,
    language: d.language,
    year: d.year,
    university: d.university,
    city: d.city,
    publisher: d.publisher,
    journal: d.journal,
    volume: d.volume,
    issue: d.issue,
    pages: d.pages,
    url: d.url,
    doi: d.doi,
    topics: d.topics,
    advisors: d.advisors,
    department: d.department,
    pageCount: d.pageCount,
    fullText: d.fullText,
    abstract: d.abstract,
  };
}

export function bibtex(w: Work): string {
  return toBibtex(record(w));
}
