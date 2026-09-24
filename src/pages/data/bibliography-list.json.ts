import { getWorks, displayName, universityName } from '../../lib/works';

/**
 * Compact, language-neutral rows for the bibliography page, which renders its list
 * in the browser (the site holds thousands of theses; one HTML list per language
 * would be several megabytes). Order of fields — see `Row` in bibliography/index.astro:
 * [id, type, language, university, universityFull, advisors, topics, year, pageCount,
 *  hasAbstract, fullText, title, authors, city, abstractSnippet]
 */
const snippet = (s?: string) => (s && s.length > 260 ? `${s.slice(0, 257).replace(/\s+\S*$/, '')}…` : (s ?? ''));

export async function GET() {
  const works = await getWorks();
  const rows = works.map((w) => {
    const d = w.data;
    return [
      w.id,
      d.type,
      d.language,
      universityName(d.university),
      d.university ?? '',
      d.advisors,
      d.topics,
      d.year ?? null,
      d.pageCount ?? null,
      d.abstract ? 1 : 0,
      d.fullText ?? '',
      d.title,
      d.authors.map(displayName).join(', '),
      d.city ?? '',
      snippet(d.abstract),
    ];
  });
  return new Response(JSON.stringify(rows), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
}
