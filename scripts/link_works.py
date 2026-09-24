"""Link bibliography records to the jurists named in their titles.

Writes src/data/work-scholars.json ({work id: [jurist ids]}) and a report in
sources/work-scholars-report.txt. A jurist is linked only through a nisba
(el-/er-/es-… name) that belongs to no other jurist, is not a place name and is
not a generic epithet. If the title gives a laqab ending in -eddin/-üddin just
before the nisba and the jurist's own name has a laqab, the two must agree; a nisba
that follows "Ebu'l-/Ebi'l-" is a kunya and is ignored. EXCLUDE lists namesakes
found on review.
"""
import json, re, unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / "src/data/work-scholars.json"
REPORT = ROOT / "sources/work-scholars-report.txt"

GENERIC = {"kebir", "sagir", "ensari", "arabi", "hanefi", "kurasi", "efendi", "hasimi", "alevi", "hanbeli", "maliki", "safii"}
PARTICLES = {"el", "er", "es", "et", "ez", "en", "ed", "ec", "eb", "b", "bin", "ibn", "ibnu", "ibni"}
# (nisba, word in the title) pairs that identify a namesake, not our jurist.
EXCLUDE = {("imrani", "yahya"), ("ayintabi", "mehmed"), ("ayintabi", "munib"), ("imadi", "celaleddin")}


def norm(s: str) -> str:
    s = s.replace("ı", "i").replace("İ", "i").replace("I", "i")
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def laqab(w: str) -> str:
    return re.sub(r"(uddin|iddin)$", "eddin", w)


def main():
    places = {norm(n) for n in re.findall(r'tr: "([^"]+)"', (ROOT / "src/data/places.yaml").read_text())}
    alias, names = defaultdict(set), {}
    for f in (ROOT / "src/content/scholars").glob("*.md"):
        tr = re.search(r'tr: "([^"]+)"', f.read_text()).group(1)
        names[f.stem] = {laqab(w) for w in norm(tr).split()}
        m = re.search(r"\b(?:el|er|es|et|ez|en|ed|eş|ec|eb)-(\S+)$", tr)
        if not m:
            continue
        a = norm(m.group(1))
        if len(a) >= 5 and a not in GENERIC and a not in places:
            alias[a].add(f.stem)
    unique = {a: next(iter(ids)) for a, ids in alias.items() if len(ids) == 1}

    links, report = {}, []
    for f in sorted((ROOT / "src/content/works").glob("*.yaml")):
        title = json.loads(re.search(r"^title: (.*)$", f.read_text(), re.M).group(1))
        words = norm(title).split()
        for i, w in enumerate(words):
            if w not in unique:
                continue
            sid = unique[w]
            before = [x for x in words[max(0, i - 3) : i] if x not in PARTICLES]
            why = None
            if i >= 2 and words[i - 1] == "l" and words[i - 2] in {"ebu", "ebi", "eba"}:
                why = "kunya"
            elif (own := [n for n in names[sid] if re.search(r"(eddin|uddin|iddin)", n)]) and any(
                laqab(x) not in own for x in before if laqab(x).endswith("eddin")
            ):
                why = "different laqab"
            elif any((w, x) in EXCLUDE for x in words):
                why = "namesake"
            report.append(f"{'SKIP ' + why if why else 'LINK'}\t{w}\t{sid}\t{f.stem}\t{title}")
            if not why:
                links.setdefault(f.stem, [])
                if sid not in links[f.stem]:
                    links[f.stem].append(sid)
    OUT.write_text(json.dumps(links, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"{sum(len(v) for v in links.values())} links in {len(links)} records → {OUT.name}")


if __name__ == "__main__":
    main()
