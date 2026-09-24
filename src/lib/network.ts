import links from '../data/links.json';

type Role = 'teachers' | 'students';
type Links = Record<string, Partial<Record<Role, Record<string, string>>>>;
const LINKS = links as Links;

/** The entry a teacher/student name in an entry's list refers to, when matched. */
export function refLink(id: string, role: Role, index: number): string | undefined {
  return LINKS[id]?.[role]?.[String(index)];
}

/** Every teacher → student pair, whichever of the two entries mentions it. */
export const EDGES: [string, string][] = (() => {
  const seen = new Set<string>();
  const out: [string, string][] = [];
  for (const [id, roles] of Object.entries(LINKS)) {
    for (const [role, map] of Object.entries(roles) as [Role, Record<string, string>][]) {
      for (const other of Object.values(map)) {
        const edge: [string, string] = role === 'teachers' ? [other, id] : [id, other];
        const key = edge.join('>');
        if (!seen.has(key)) {
          seen.add(key);
          out.push(edge);
        }
      }
    }
  }
  return out;
})();

export function neighbours(id: string) {
  return {
    teachers: EDGES.filter(([, s]) => s === id).map(([t]) => t),
    students: EDGES.filter(([t]) => t === id).map(([, s]) => s),
  };
}
