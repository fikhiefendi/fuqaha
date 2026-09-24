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

export type MapScholar = { name: string; ar: string; href: string; c: number; life: string };

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
  const t = useT(lang);
  const roleLabels = Object.fromEntries(ROLES.map((r) => [r, t(`role.${r}` as UIKey)]));
  return { places: mapPlaces, scholars: list, roleLabels };
}
