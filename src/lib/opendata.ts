import { getCollection } from 'astro:content';
import { getScholars } from './scholars';
import { miladi } from './hijri';
import { EDGES } from './network';

const SITE_URL = 'https://fikhiefendi.github.io/fuqaha';

/** One flat record per jurist for the open-data downloads. */
export async function scholarRecords() {
  const places = new Map((await getCollection('places')).map((p) => [p.id, p.data]));
  const place = (id?: string) => (id ? { id, name: places.get(id)?.name.tr ?? id, lat: places.get(id)?.lat, lng: places.get(id)?.lng } : undefined);
  return (await getScholars()).map((s) => {
    const d = s.data;
    const src = d.sources[0];
    return {
      id: s.id,
      url: `${SITE_URL}/tr/scholars/${s.id}/`,
      nameAr: d.name.ar,
      nameTr: d.name.tr,
      nameEn: d.name.en,
      madhhab: d.madhhab,
      birthHijri: d.birth?.hijri,
      birthGregorian: d.birth?.hijri ? miladi(d.birth.hijri, d.birth.month, d.birth.day) : undefined,
      birthPlace: place(d.birth?.place),
      deathHijri: d.death.hijri,
      deathGregorian: d.death.hijri ? miladi(d.death.hijri, d.death.month, d.death.day) : undefined,
      deathApprox: d.death.approx,
      deathPlace: place(d.death.place),
      places: d.places.map((p) => ({ ...place(p.place), role: p.role })),
      teachers: d.teachers,
      students: d.students,
      teacherIds: EDGES.filter(([, st]) => st === s.id).map(([t]) => t),
      studentIds: EDGES.filter(([t]) => t === s.id).map(([, st]) => st),
      works: d.works.map((w) => w.ar),
      source: { book: src.book, page: src.page, entry: src.entry },
    };
  });
}
