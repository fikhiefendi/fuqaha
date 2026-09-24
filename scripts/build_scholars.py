"""Build jurist entries from al-Laknawi's al-Fawa'id al-bahiyya.

Inputs:
  sources/fawaid-entries.json   parsed Arabic text (scripts/parse_fawaid.py)
  sources/extracted/*.json      fields read from each entry (names, dates, places…)
Output:
  src/content/scholars/<slug>.md  one file per entry; the Arabic text is the body.

Run: python3 scripts/build_scholars.py
"""
import glob, json, re, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / "src/content/scholars"
sys.path.insert(0, str(ROOT / "scripts"))
from places import PLACES  # noqa: E402

SOURCE = {
    "book": "الفوائد البهية في تراجم الحنفية",
    "bookTr": "el-Fevâidü'l-behiyye fî terâcimi'l-Hanefiyye",
    "author": "أبو الحسنات محمد عبد الحي اللكنوي (ت 1304هـ)",
    "authorTr": "Ebu'l-Hasenat Abdülhay el-Leknevi (ö. 1304/1887)",
    "edition": "Mısır: Matbaatü Dâri's-saâde, 1324",
}
ADDED = "2026-09-23"
# A few well-known jurists shown in the home-page slider.
FEATURED = {48, 39, 45, 93, 158, 122, 206, "191j"}

TR = str.maketrans({"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ç": "c", "Ç": "c",
                    "ö": "o", "Ö": "o", "ü": "u", "Ü": "u", "â": "a", "Â": "a", "î": "i", "û": "u"})


def slugify(name: str) -> str:
    s = name.translate(TR).lower()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[''`]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def q(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def date_yaml(prefix: str, x: dict) -> list[str]:
    h = x.get(prefix)
    if h is None and not x.get(prefix + "p"):
        return []
    lines = [f"{'birth' if prefix == 'b' else 'death'}:"]
    if h is not None:
        lines.append(f"  hijri: {h}")
    for key, name in (("m", "month"), ("d", "day")):
        v = x.get(prefix + key)
        if v is not None:
            lines.append(f"  {name}: {v}")
    if x.get(prefix + "approx"):
        lines.append("  approx: true")
    if x.get(prefix + "alt"):
        lines.append(f"  alt: {json.dumps(x[prefix + 'alt'])}")
    if x.get(prefix + "p"):
        lines.append(f"  place: {x[prefix + 'p']}")
    return lines


def main():
    entries = {str(e["n"]): e for e in json.loads((ROOT / "sources/fawaid-entries.json").read_text())}
    extracted = {}
    for f in sorted(glob.glob(str(ROOT / "sources/extracted/*.json"))):
        for x in json.loads(Path(f).read_text()):
            extracted[str(x["n"])] = x

    missing_places = set()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.md"):
        old.unlink()

    used = {}
    order = list(entries)
    for n in order:
        x = extracted.get(n)
        if not x:
            continue
        e = entries[n]
        slug = slugify(x["tr"])
        if slug in used:
            slug = f"{slug}-{n}"
        used[slug] = n

        for pid in [p for p, _ in x.get("pl", [])] + [x.get("dp"), x.get("bp")]:
            if pid and pid not in PLACES:
                missing_places.add(pid)

        heading = re.sub(r"[()\[\]]", "", e["heading"]).strip()
        pages = str(e["pageStart"]) if e["pageStart"] == e["pageEnd"] else f"{e['pageStart']}-{e['pageEnd']}"
        fm = [
            "---",
            f"name: {{ ar: {q(x['ar'])}, tr: {q(x['tr'])}, en: {q(x['en'])} }}",
            f"fullNameAr: {q(heading)}",
            "madhhab: hanefi",
            *date_yaml("b", x),
            *date_yaml("d", x),
        ]
        if not x.get("d") and not x.get("dp"):
            fm.append("death: {}")
        if x.get("pl"):
            fm.append("places:")
            fm += [f"  - {{ place: {p}, role: {r} }}" for p, r in x["pl"]]
        for key, field in (("t", "teachers"), ("s", "students")):
            if x.get(key):
                fm.append(f"{field}: {json.dumps(x[key], ensure_ascii=False)}")
        if x.get("w"):
            fm.append("works:")
            fm += [f"  - {{ ar: {q(w)} }}" for w in x["w"]]
        fm += [
            f"summary: {{ tr: {q(x['str'])}, en: {q(x['sen'])} }}",
            f"addedAt: {ADDED}",
            f"order: {order.index(n) + 1}",
            f"featured: {'true' if (n in {str(f) for f in FEATURED}) else 'false'}",
            "sources:",
            f"  - book: {q(SOURCE['book'])}",
            f"    bookTr: {q(SOURCE['bookTr'])}",
            f"    author: {q(SOURCE['author'])}",
            f"    authorTr: {q(SOURCE['authorTr'])}",
            f"    edition: {q(SOURCE['edition'])}",
            f"    page: {q(pages)}",
            f"    entry: {q(n)}",
            "---",
            "",
        ]
        body = f"**{heading}**\n\n{e['text']}\n"
        (OUT / f"{slug}.md").write_text("\n".join(fm) + body, encoding="utf-8")

    done = sum(1 for n in order if n in extracted)
    print(f"{done}/{len(order)} entries written to {OUT}")
    if missing_places:
        print("Unknown place ids:", sorted(missing_places))
        sys.exit(1)


if __name__ == "__main__":
    main()
