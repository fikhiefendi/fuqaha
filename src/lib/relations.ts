// Cross-references between bibliography records, and between records and jurists.
import workScholars from '../data/work-scholars.json';
import { getWorks, type Work } from './works';

const LINKS = workScholars as Record<string, string[]>;

/** Jurists (ids) named in a record's title. */
export const scholarsOf = (workId: string) => LINKS[workId] ?? [];

/** Records whose titles name the jurist. */
export const worksAbout = (scholarId: string) =>
  Object.entries(LINKS)
    .filter(([, ids]) => ids.includes(scholarId))
    .map(([id]) => id);

const STOP = new Set(
  (
    'islam islami islamda islamin hukuk hukuku hukukunda hukukuna hukuki hukukta hukukunun fikih fikhi fikhinda fikhina fikhinin fikhin ' +
    've ile bir bu su da de ki mi icin olarak gibi daha cok en her olan olup olmak olmasi olmakla ise ancak ayrica bunun bunlar bunlarin ' +
    'bu nedenle sonra once kadar diger tum baska aynı ayni icinde uzerinde uzerine hakkinda acisindan gore baglaminda cercevesinde ' +
    'calisma calismada calismanin calismamizda tez tezde tezin bolum bolumde bolumunde birinci ikinci ucuncu dorduncu son sonuc giris ' +
    'konu konusu konusunda ele alinmis alinmistir incelenmistir incelenmis yapilmistir edilmistir edilmis olunmustur ortaya konulmustur ' +
    'amaclanmistir hedeflenmistir tespit degerlendirilmistir anlayisi meselesi meseleleri ornegi orneginde nin nun in un ın un da de ' +
    'the of and in on for a an to with by is are this that from as'
  ).split(' '),
);

function tokens(s: string): string[] {
  return s
    .toLocaleLowerCase('tr')
    .replace(/ı/g, 'i')
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .split(/[^a-z0-9؀-ۿ]+/)
    .filter((w) => w.length > 3 && !STOP.has(w))
    .map((w) => w.slice(0, 7));
}

let cache: Promise<Map<string, { id: string; score: number }[]>> | undefined;

/** For every record, the most similar others (cosine over tf-idf of title, topics and abstract). */
function similarity() {
  cache ??= getWorks().then((works) => {
    const docs = works.map((w) => {
      const tf = new Map<string, number>();
      const add = (ws: string[], weight: number) => ws.forEach((t) => tf.set(t, (tf.get(t) ?? 0) + weight));
      add(tokens(w.data.title), 3);
      add(w.data.topics.flatMap(tokens), 2);
      add(tokens(w.data.abstract ?? ''), 1);
      return { id: w.id, tf };
    });
    const df = new Map<string, number>();
    docs.forEach((d) => d.tf.forEach((_, t) => df.set(t, (df.get(t) ?? 0) + 1)));
    const N = docs.length;
    const vecs = docs.map((d) => {
      const v = new Map<string, number>();
      d.tf.forEach((f, t) => {
        const n = df.get(t)!;
        if (n < 2 || n > N * 0.2) return;
        v.set(t, (1 + Math.log(f)) * Math.log(N / n));
      });
      const len = Math.hypot(...v.values()) || 1;
      v.forEach((x, t) => v.set(t, x / len));
      return v;
    });
    // Inverted index keeps the comparison to records that share a term.
    const index = new Map<string, number[]>();
    vecs.forEach((v, i) => v.forEach((_, t) => (index.get(t) ?? index.set(t, []).get(t)!).push(i)));
    const out = new Map<string, { id: string; score: number }[]>();
    vecs.forEach((v, i) => {
      const acc = new Map<number, number>();
      v.forEach((x, t) => index.get(t)!.forEach((j) => j !== i && acc.set(j, (acc.get(j) ?? 0) + x * vecs[j].get(t)!)));
      out.set(
        docs[i].id,
        [...acc]
          .filter(([, s]) => s >= 0.12)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 6)
          .map(([j, score]) => ({ id: docs[j].id, score })),
      );
    });
    return out;
  });
  return cache;
}

export async function similarTo(w: Work) {
  return (await similarity()).get(w.id) ?? [];
}

export function sameAdvisor(w: Work, all: Work[]) {
  if (!w.data.advisors.length) return [];
  const mine = new Set(w.data.advisors);
  return all.filter((o) => o.id !== w.id && o.data.advisors.some((a) => mine.has(a)));
}
