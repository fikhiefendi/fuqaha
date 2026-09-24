// Layered "silsila" layout: teachers above, students below, two generations
// each way. Pure functions so the same drawing is made at build time (jurist
// pages) and in the browser (network page).

export type Person = { name: string; ar: string; life: string; href: string; year: number | null };
type Edge = [string, string];

export type Lineage = {
  rows: { gen: number; ids: string[]; more: number }[];
  edges: Edge[];
};

export function lineage(id: string, edges: Edge[], year: (id: string) => number | null, depth = 2, perRow = 9): Lineage {
  const teachersOf = (x: string) => edges.filter(([, s]) => s === x).map(([t]) => t);
  const studentsOf = (x: string) => edges.filter(([t]) => t === x).map(([, s]) => s);
  const gen = new Map<string, number>([[id, 0]]);
  const more = new Map<number, number>();
  for (const [dir, next] of [[-1, teachersOf], [1, studentsOf]] as const) {
    let frontier = [id];
    for (let d = 1; d <= depth; d++) {
      const found = [...new Set(frontier.flatMap(next))].filter((n) => !gen.has(n));
      const byYear = found.sort((a, b) => (year(a) ?? 9999) - (year(b) ?? 9999));
      const kept = byYear.slice(0, perRow);
      if (found.length > kept.length) more.set(dir * d, found.length - kept.length);
      kept.forEach((n) => gen.set(n, dir * d));
      frontier = kept;
      if (!frontier.length) break;
    }
  }
  const used = edges.filter(([t, s]) => gen.has(t) && gen.has(s) && gen.get(s)! - gen.get(t)! === 1);
  const gens = [...new Set(gen.values())].sort((a, b) => a - b);
  const rows = new Map<number, string[]>(gens.map((g) => [g, [...gen].filter(([, v]) => v === g).map(([k]) => k)]));

  // Order outer rows by the mean position of their links in the inner row,
  // which keeps the lines from crossing more than they must.
  const order = (g: number, inner: number) => {
    const ref = rows.get(inner)!;
    const pos = (n: string) => {
      const peers = used.filter(([t, s]) => (t === n && gen.get(s) === inner) || (s === n && gen.get(t) === inner)).map(([t, s]) => ref.indexOf(t === n ? s : t));
      return peers.length ? peers.reduce((a, b) => a + b, 0) / peers.length : 0;
    };
    rows.set(g, rows.get(g)!.sort((a, b) => pos(a) - pos(b) || (year(a) ?? 0) - (year(b) ?? 0)));
  };
  for (const g of gens.filter((g) => g < -1).sort((a, b) => b - a)) order(g, g + 1);
  for (const g of gens.filter((g) => g > 1)) order(g, g - 1);

  return { rows: gens.map((g) => ({ gen: g, ids: rows.get(g)!, more: more.get(g) ?? 0 })), edges: used };
}

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);
const clip = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

/** SVG drawing of a lineage; `labels` gives row captions by generation. */
export function lineageSvg(
  l: Lineage,
  person: (id: string) => Person,
  opts: { self: string; rtl: boolean; labels: Record<number, string>; moreLabel: (n: number) => string; showLatin: boolean },
) {
  const W = 204;
  const H = 62;
  const GX = 14;
  const GY = 70;
  const PAD = 30;
  const CAP = 110;
  const widest = Math.max(...l.rows.map((r) => r.ids.length + (r.more ? 0.6 : 0)));
  const width = Math.max(widest * (W + GX) - GX, W * 2) + PAD * 2 + CAP;
  const pos = new Map<string, [number, number]>();
  l.rows.forEach((r, ri) => {
    const rowW = r.ids.length * (W + GX) - GX;
    const x0 = (opts.rtl ? PAD : CAP + PAD) + (width - CAP - PAD * 2 - rowW) / 2;
    const ids = opts.rtl ? [...r.ids].reverse() : r.ids;
    ids.forEach((id, i) => pos.set(id, [x0 + i * (W + GX), PAD + ri * (H + GY)]));
  });
  const height = PAD * 2 + l.rows.length * (H + GY) - GY;

  const links = l.edges
    .map(([t, s]) => {
      const [tx, ty] = pos.get(t)!;
      const [sx, sy] = pos.get(s)!;
      const x1 = tx + W / 2;
      const y1 = ty + H;
      const x2 = sx + W / 2;
      const y2 = sy;
      const my = (y1 + y2) / 2;
      const hot = t === opts.self || s === opts.self;
      return `<path class="ln${hot ? ' hot' : ''}" d="M${x1} ${y1}C${x1} ${my} ${x2} ${my} ${x2} ${y2}"/>`;
    })
    .join('');

  const captions = l.rows
    .map((r, ri) => {
      const y = PAD + ri * (H + GY) + H / 2;
      const more = r.more ? `<text class="more" x="${opts.rtl ? PAD : width - PAD}" y="${y + H / 2 + 14}" text-anchor="${opts.rtl ? 'start' : 'end'}">${esc(opts.moreLabel(r.more))}</text>` : '';
      return `<text class="cap" x="${opts.rtl ? width - 12 : 12}" y="${y + 4}" text-anchor="${opts.rtl ? 'end' : 'start'}">${esc(opts.labels[r.gen] ?? '')}</text>${more}`;
    })
    .join('');

  const nodes = [...pos]
    .map(([id, [x, y]]) => {
      const p = person(id);
      const self = id === opts.self;
      const cx = x + W / 2;
      return `<a href="${esc(p.href)}" class="nd${self ? ' self' : ''}" data-id="${esc(id)}">
        <rect x="${x}" y="${y}" width="${W}" height="${H}" rx="3"/>
        <rect class="inner" x="${x + 3}" y="${y + 3}" width="${W - 6}" height="${H - 6}" rx="2"/>
        <text class="ar" x="${cx}" y="${y + (opts.showLatin ? 23 : 29)}" text-anchor="middle" direction="rtl">${esc(clip(p.ar, 28))}</text>
        ${opts.showLatin ? `<text class="la" x="${cx}" y="${y + 39}" text-anchor="middle">${esc(clip(p.name, 34))}</text>` : ''}
        <text class="yr" x="${cx}" y="${y + (opts.showLatin ? 53 : 48)}" text-anchor="middle">${esc(p.life)}</text>
      </a>`;
    })
    .join('');

  return `<svg class="lineage" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" role="img">${captions}${links}${nodes}</svg>`;
}
