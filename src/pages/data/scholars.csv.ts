import { scholarRecords } from '../../lib/opendata';

const COLS = ['id', 'nameAr', 'nameTr', 'nameEn', 'madhhab', 'birthHijri', 'birthGregorian', 'birthPlace', 'deathHijri', 'deathGregorian', 'deathPlace', 'teacherIds', 'studentIds', 'sourcePage', 'sourceEntry', 'url'];

export async function GET() {
  const cell = (v: unknown) => {
    const s = Array.isArray(v) ? v.join('; ') : v === undefined || v === null ? '' : String(v);
    return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const rows = (await scholarRecords()).map((r) =>
    [r.id, r.nameAr, r.nameTr, r.nameEn, r.madhhab, r.birthHijri, r.birthGregorian, r.birthPlace?.name, r.deathHijri, r.deathGregorian, r.deathPlace?.name, r.teacherIds, r.studentIds, r.source.page, r.source.entry, r.url]
      .map(cell)
      .join(','),
  );
  return new Response('﻿' + [COLS.join(','), ...rows].join('\r\n'), { headers: { 'Content-Type': 'text/csv; charset=utf-8' } });
}
