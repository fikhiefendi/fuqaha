// Bibliographic export formats. Pure functions over plain records so the same
// code runs at build time (static files) and in the browser (filtered export).

export type Rec = {
  id: string;
  type: string;
  title: string;
  authors: string[];
  editors?: string[];
  language: string;
  year?: number;
  university?: string;
  city?: string;
  publisher?: string;
  journal?: string;
  volume?: string | number;
  issue?: string | number;
  pages?: string;
  url?: string;
  doi?: string;
  topics: string[];
  advisors?: string[];
  department?: string;
  pageCount?: number;
  fullText?: string;
  abstract?: string;
};

const THESIS_LABEL: Record<string, string> = { 'tez-doktora': 'Doktora Tezi', 'tez-yl': 'Yüksek Lisans Tezi' };

export function toBibtex(r: Rec): string {
  const kind =
    r.type === 'tez-doktora' ? 'phdthesis' : r.type === 'tez-yl' ? 'mastersthesis' : r.type === 'makale' ? 'article' : r.type === 'bildiri' ? 'inproceedings' : 'book';
  const clean = (v: string | number) => String(v).replace(/[{}]/g, '');
  const f: [string, string | number | undefined][] = [
    ['author', r.authors.join(' and ')],
    ['editor', r.editors?.length ? r.editors.join(' and ') : undefined],
    ['title', r.title],
    ['school', r.university],
    ['address', r.city],
    ['journal', r.journal],
    ['volume', r.volume],
    ['number', r.issue],
    ['pages', r.pages],
    ['publisher', r.publisher],
    ['year', r.year],
    ['language', r.language],
    ['keywords', r.topics.length ? r.topics.join(', ') : undefined],
    ['pagetotal', r.pageCount],
    ['note', r.advisors?.length ? `Danışman: ${r.advisors.join(', ')}` : undefined],
    ['abstract', r.abstract],
    ['doi', r.doi],
    ['url', r.url],
  ];
  const body = f
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `  ${k} = {${clean(v!)}}`)
    .join(',\n');
  return `@${kind}{${r.id.replace(/-/g, '_')},\n${body}\n}`;
}

export function toRis(r: Rec): string {
  const ty = r.type.startsWith('tez') ? 'THES' : r.type === 'makale' ? 'JOUR' : r.type === 'bildiri' ? 'CPAPER' : r.type === 'kitap' ? 'BOOK' : 'GEN';
  const lines: [string, string | number | undefined][] = [
    ['TY', ty],
    ...r.authors.map((a): [string, string] => ['AU', a]),
    ...(r.editors ?? []).map((a): [string, string] => ['ED', a]),
    ['TI', r.title],
    ['T2', r.journal],
    ['VL', r.volume],
    ['IS', r.issue],
    ['SP', r.pages],
    ['PY', r.year],
    ['PB', r.university ?? r.publisher],
    ['CY', r.city],
    ['M3', THESIS_LABEL[r.type]],
    ...(r.advisors ?? []).map((a): [string, string] => ['A3', a]),
    ['N1', r.department],
    ['AB', r.abstract],
    ['LA', r.language],
    ...r.topics.map((k): [string, string] => ['KW', k]),
    ['DO', r.doi],
    ['UR', r.url],
    ['L1', r.fullText],
  ];
  return [...lines.filter(([, v]) => v !== undefined && v !== '').map(([k, v]) => `${k}  - ${v}`), 'ER  - '].join('\r\n');
}

const CSV_COLS: (keyof Rec)[] = ['id', 'type', 'title', 'authors', 'advisors', 'year', 'university', 'department', 'city', 'pageCount', 'publisher', 'journal', 'language', 'topics', 'doi', 'url', 'fullText', 'abstract'];

export function toCsv(recs: Rec[]): string {
  const cell = (v: unknown) => {
    const s = Array.isArray(v) ? v.join('; ') : v === undefined ? '' : String(v);
    return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  // Leading BOM so spreadsheet programs read the Turkish letters correctly.
  return '﻿' + [CSV_COLS.join(','), ...recs.map((r) => CSV_COLS.map((c) => cell(r[c])).join(','))].join('\r\n');
}

/** OpenURL ContextObject in a span (COinS): lets Zotero pick up the record. */
export function coins(r: Rec): string {
  const p = new URLSearchParams({ ctx_ver: 'Z39.88-2004' });
  if (r.type.startsWith('tez')) {
    p.set('rft_val_fmt', 'info:ofi/fmt:kev:mtx:dissertation');
    p.set('rft.title', r.title);
    if (r.university) p.set('rft.inst', r.university);
    p.set('rft.degree', THESIS_LABEL[r.type] ?? '');
  } else if (r.type === 'makale') {
    p.set('rft_val_fmt', 'info:ofi/fmt:kev:mtx:journal');
    p.set('rft.genre', 'article');
    p.set('rft.atitle', r.title);
    if (r.journal) p.set('rft.jtitle', r.journal);
  } else {
    p.set('rft_val_fmt', 'info:ofi/fmt:kev:mtx:book');
    p.set('rft.genre', 'book');
    p.set('rft.btitle', r.title);
    if (r.publisher) p.set('rft.pub', r.publisher);
  }
  r.authors.forEach((a) => p.append('rft.au', a));
  if (r.year) p.set('rft.date', String(r.year));
  if (r.city) p.set('rft.place', r.city);
  if (r.language) p.set('rft.language', r.language);
  if (r.doi) p.set('rft_id', `info:doi/${r.doi}`);
  else if (r.url) p.set('rft_id', r.url);
  return p.toString();
}
