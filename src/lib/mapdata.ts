import { getCollection } from 'astro:content';
import { pick, useT, type Lang, type UIKey } from '../i18n/ui';
import { getScholars, lifeShort, scholarCentury, type Scholar } from './scholars';
import { href } from './url';

export type Role = 'nisbe' | 'dogum' | 'vefat' | 'ikamet' | 'rihle' | 'ders' | 'kadilik';
export const ROLES: Role[] = ['dogum', 'vefat', 'ikamet', 'ders', 'kadilik', 'rihle', 'nisbe'];

/** Every place a jurist is linked to, with roles (birth/death places are folded in). */
export function scholarPlaces(s: Scholar): Map<string, Set<Role>> {
  const map = new Map<string, Set<Role>>();
  const add = (id: string | undefined, role: Role) => {
    if (!id) return;
    if (!map.has(id)) map.set(id, new Set());
    map.get(id)!.add(role);
  };
  s.data.places.forEach((p) => add(p.place, p.role));
  add(s.data.birth?.place, 'dogum');
  add(s.data.death.place, 'vefat');
  return map;
}

export type MapPlace = {
  id: string;
  name: string;
  nameAr: string;
  region: string;
  lat: number;
  lng: number;
  uri?: string;
  approx: boolean;
  /** [scholar index, roles] */
  links: [number, Role[]][];
};

/** `p`: the jurist's places in life order (birth, study and work, death). */
export type MapScholar = { name: string; ar: string; href: string; c: number; life: string; p: string[] };

const LIFE_ORDER: Role[] = ['dogum', 'nisbe', 'rihle', 'ders', 'ikamet', 'kadilik', 'vefat'];

/** A jurist's places ordered as a journey: birth first, death last. */
export function lifeRoute(s: Scholar): string[] {
  const rank = (roles: Set<Role>) => Math.min(...[...roles].map((r) => LIFE_ORDER.indexOf(r)));
  const ordered = [...scholarPlaces(s)].sort((a, b) => rank(a[1]) - rank(b[1]));
  const dead = ordered.findIndex(([, roles]) => roles.has('vefat'));
  if (dead >= 0) ordered.push(...ordered.splice(dead, 1));
  return ordered.map(([id]) => id);
}

export async function getMapData(lang: Lang, only?: Scholar[]) {
  const places = await getCollection('places');
  const scholars = only ?? (await getScholars());
  const byPlace = new Map<string, [number, Role[]][]>();
  const list: MapScholar[] = scholars.map((s, i) => {
    scholarPlaces(s).forEach((roles, pid) => {
      if (!byPlace.has(pid)) byPlace.set(pid, []);
      byPlace.get(pid)!.push([i, [...roles]]);
    });
    return {
      name: lang === 'ar' ? s.data.name.ar : s.data.name[lang],
      ar: s.data.name.ar,
      href: href(lang, `scholars/${s.id}/`),
      c: scholarCentury(s) ?? 0,
      life: lifeShort(s, lang),
      p: lifeRoute(s),
    };
  });
  const mapPlaces: MapPlace[] = places
    .filter((p) => byPlace.has(p.id))
    .map((p) => ({
      id: p.id,
      name: pick(p.data.name, lang) ?? p.id,
      nameAr: p.data.name.ar ?? '',
      region: pick(p.data.region, lang) ?? '',
      lat: p.data.lat,
      lng: p.data.lng,
      uri: p.data.uri,
      approx: p.data.coordSource !== 'thurayya',
      links: byPlace.get(p.id)!,
    }));
  // Iqlim labels at the centre of each region's places.
  const byRegion = new Map<string, { name: string; nameAr: string; lat: number[]; lng: number[] }>();
  for (const pl of places.filter((x) => byPlace.has(x.id))) {
    const r = byRegion.get(pl.data.regionId) ?? { name: pick(pl.data.region, lang) ?? '', nameAr: pl.data.region.ar ?? '', lat: [], lng: [] };
    r.lat.push(pl.data.lat);
    r.lng.push(pl.data.lng);
    byRegion.set(pl.data.regionId, r);
  }
  const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;
  const regions = [...byRegion.values()]
    .filter((r) => r.lat.length >= 2)
    .map((r) => ({ name: r.name, nameAr: r.nameAr, lat: mean(r.lat) - 0.8, lng: mean(r.lng) }));
  const t = useT(lang);
  const roleLabels = Object.fromEntries(ROLES.map((r) => [r, t(`role.${r}` as UIKey)]));
  return { places: mapPlaces, scholars: list, roleLabels, regions };
}
