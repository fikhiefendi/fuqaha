"""Link free-text teacher/student names to jurist entries (src/data/links.json).

Only confident matches are kept: every word of exactly one entry's Arabic name
(fathers' names included, only "b./Abu" particles and honorifics skipped) must
occur in the reference in the same order, the name must have at least two
uncommon words, and the two lives must be chronologically plausible.
Everything else stays plain text on the site.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCH = ROOT / "src/content/scholars"
OUT = ROOT / "src/data/links.json"

PARTICLES = set("بن ابن ابو ابي ابا بنت الامام الشيخ القاضي المولي صاحب".split())
COMMON = set("بن ابن ابو ابي ابا بنت عبد الله محمد احمد علي عمر عثمان حسن حسين الحسن الحسين ابراهيم يوسف محمود اسماعيل الدين الامام الشيخ القاضي".split())
DIAC = re.compile(r"[ً-ْٰـ]")

def norm(s: str) -> str:
    s = DIAC.sub("", s)
    s = re.sub("[أإآٱ]", "ا", s).replace("ة", "ه").replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"[^ء-ي\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def words(s: str): return norm(s).split()

def front(text: str):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else ""

def field(fm: str, key: str):
    m = re.search(rf"^{key}: (.*)$", fm, re.M)
    return json.loads(m.group(1)) if m else []

def death(fm: str):
    m = re.search(r"^death:\n  hijri: (\d+)", fm, re.M)
    return int(m.group(1)) if m else None

people = []
for f in sorted(SCH.glob("*.md")):
    fm = front(f.read_text(encoding="utf-8"))
    ar = re.search(r'name: \{ ar: "([^"]+)"', fm).group(1)
    seq = [w for w in words(ar) if w not in PARTICLES]
    key = {w for w in seq if w not in COMMON}
    people.append(dict(id=f.stem, ar=ar, seq=seq, key=key, death=death(fm),
                       teachers=field(fm, "teachers"), students=field(fm, "students")))

def in_order(seq, ref_words):
    it = iter(ref_words)
    return all(w in it for w in seq)

def candidates(ref: str):
    rw = words(ref)
    return [p for p in people if len(p["key"]) >= 2 and in_order(p["seq"], rw)]

def plausible(teacher, student):
    a, b = teacher["death"], student["death"]
    return a is None or b is None or (-15 <= b - a <= 120)

links, stats = {}, dict(refs=0, linked=0, ambiguous=0, implausible=0)
for p in people:
    for role in ("teachers", "students"):
        for i, ref in enumerate(p[role]):
            stats["refs"] += 1
            c = [x for x in candidates(ref) if x["id"] != p["id"]]
            if len(c) > 1:
                stats["ambiguous"] += 1
            if len(c) != 1:
                continue
            other = c[0]
            t, s = (other, p) if role == "teachers" else (p, other)
            if not plausible(t, s):
                stats["implausible"] += 1
                continue
            links.setdefault(p["id"], {}).setdefault(role, {})[str(i)] = other["id"]
            stats["linked"] += 1
OUT.write_text(json.dumps(links, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
print(stats)
