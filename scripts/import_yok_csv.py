"""Merge a YÖK thesis list (Notion CSV export) into the bibliography.

Usage: python3 scripts/import_yok_csv.py "path/to/Tezler_all.csv" [--dry-run]

Columns used: Yazar, Danışman, Detay Sayfası, PDF İndirme Linki, Sayfa Sayısı,
Tez Adı, Tür, Yıl, Özet, Üniversite.

- A row is the same thesis as an existing record when the author's surname
  matches and either the titles are close (ratio >= 0.8) or they share a
  distinctive word and the years agree (or the record has no year yet).
- Existing records are only completed: a field already present is never
  overwritten. New theses are written in the same YAML form as import_bib.py.
- A report of every decision is written to sources/yok-merge-report.txt.
"""
import csv, difflib, json, re, sys, unicodedata
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from import_bib import language  # noqa: E402

ROOT = Path(__file__).parent.parent
OUT = ROOT / "src/content/works"
REPORT = ROOT / "sources/yok-merge-report.txt"

STOP = set(
    "islam islami islamda hukuk hukuku hukukunda hukukuna hukukta hukuki fikih fikhi fikhinda fikhina fikhinin "
    "usul usulu usulunde usulunun ve ile bir bu da de ile icin olarak acisindan gore baglaminda cercevesinde "
    "ornegi orneginde uzerine hakkinda onun nin nun in un ser seri i l el er es en ed ibn b donem donemi "
    "anlayisi anlayis kavrami teorisi ilkesi hukumleri meselesi meseleleri incelemesi degerlendirme".split()
)


def norm(s: str) -> str:
    s = s.replace("ı", "i").replace("İ", "i").replace("I", "i")
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def keywords(title: str) -> set[str]:
    return {w[:6] for w in norm(title).split() if len(w) > 3 and w not in STOP}


def tr_title(word: str) -> str:
    low = word.replace("I", "ı").replace("İ", "i").lower()
    return low[:1].replace("i", "İ").replace("ı", "I").upper() + low[1:] if low else low


def person(upper: str) -> str:
    """'AYŞE YILDIZ GÜRKAN' -> 'Ayşe Yıldız Gürkan'"""
    return " ".join("-".join(tr_title(p) for p in w.split("-")) for w in upper.split())


def inverted(upper: str) -> str:
    """'AYŞE YILDIZ GÜRKAN' -> 'Gürkan, Ayşe Yıldız' (the bibliography's author form)."""
    parts = person(upper).split()
    return f"{parts[-1]}, {' '.join(parts[:-1])}" if len(parts) > 1 else parts[0]


def clean_abstract(s: str) -> str:
    s = s.replace("_x000b_", "\n").replace("\r", "")
    s = re.sub(r"-\n(?=[a-zçğıöşü])", "", s)  # words broken at line ends
    s = re.sub(r"\s*\n\s*", " ", s)
    return re.sub(r"\s{2,}", " ", s).strip()


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.replace("ı", "i").replace("İ", "i"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def read_works():
    works = []
    for f in sorted(OUT.glob("*.yaml")):
        text = f.read_text(encoding="utf-8")
        field = lambda k: re.search(rf"^{k}: (.*)$", text, re.M)
        works.append(
            dict(
                id=f.stem,
                path=f,
                text=text,
                title=json.loads(field("title").group(1)),
                surnames={norm(a.split(",")[0]).split()[-1] for a in json.loads(field("authors").group(1)) if norm(a)},
                year=int(field("year").group(1)) if field("year") else None,
                keys=set(re.findall(r"^(\w+):", text, re.M)),
            )
        )
    return works


def same_thesis(row, w) -> tuple[bool, float]:
    ratio = difflib.SequenceMatcher(None, norm(row["Tez Adı"]), norm(w["title"])).ratio()
    year = int(row["Yıl"]) if row["Yıl"].strip().isdigit() else None
    years_agree = w["year"] is None or year is None or w["year"] == year
    if ratio >= 0.8 and (years_agree or abs(w["year"] - year) <= 1):
        return True, ratio
    shared = keywords(row["Tez Adı"]) & keywords(w["title"])
    return bool(shared) and years_agree and ratio >= 0.45, ratio


def fields_from(row, cities):
    parts = [p.strip() for p in row["Üniversite"].split(" / ")]
    university = ", ".join(parts[:2])
    advisors = [person(a.strip()) for a in row["Danışman"].split(";") if a.strip()]
    out = {
        "year": int(row["Yıl"]) if row["Yıl"].strip().isdigit() else None,
        "university": university,
        "department": " / ".join(parts[2:]) or None,
        "advisors": advisors or None,
        "pageCount": int(row["Sayfa Sayısı"]) if row["Sayfa Sayısı"].strip().isdigit() else None,
        "url": row["Detay Sayfası"].strip() or None,
        "fullText": row["PDF İndirme Linki"].strip() or None,
        "abstract": clean_abstract(row["Özet"]) or None,
        "city": cities.get(parts[0]),
    }
    return {k: v for k, v in out.items() if v}


def yaml_line(key, value):
    if isinstance(value, int):
        return f"{key}: {value}"
    return f"{key}: {json.dumps(value, ensure_ascii=False)}"


def main():
    src = Path(sys.argv[1])
    dry = "--dry-run" in sys.argv
    rows = list(csv.DictReader(src.open(encoding="utf-8-sig")))
    works = read_works()
    # University -> city, learnt from the records that already have both.
    cities = {}
    for w in works:
        u = re.search(r'^university: "([^",]+)', w["text"], re.M)
        c = re.search(r"^city: (.*)$", w["text"], re.M)
        if u and c:
            cities.setdefault(u.group(1), json.loads(c.group(1)))

    report, completed, added = [], 0, 0
    today = date.today().isoformat()
    used_ids = {w["id"] for w in works}
    for row in rows:
        surname = norm(row["Yazar"]).split()[-1]
        best = None
        for w in works:
            if surname not in w["surnames"]:
                continue
            ok, ratio = same_thesis(row, w)
            if ok and (best is None or ratio > best[1]):
                best = (w, ratio)
        new_fields = fields_from(row, cities)
        if best:
            w = best[0]
            missing = {k: v for k, v in new_fields.items() if k not in w["keys"]}
            report.append(f"MATCH {best[1]:.2f}  {w['id']}  <=  {row['Tez Adı']}  [+{', '.join(missing) or '—'}]")
            if missing:
                lines = w["text"].rstrip("\n").split("\n")
                at = next((i for i, l in enumerate(lines) if l.startswith("addedAt:")), len(lines))
                lines[at:at] = [yaml_line(k, v) for k, v in missing.items()]
                if not dry:
                    w["path"].write_text("\n".join(lines) + "\n", encoding="utf-8")
                completed += 1
            continue
        title_words = [w for w in slug(row["Tez Adı"]).split("-") if len(w) > 3][:2]
        wid = "-".join([slug(inverted(row["Yazar"]).split(",")[0]), *title_words, row["Yıl"].strip() or "nodate"])
        while wid in used_ids:
            wid += "-b"
        used_ids.add(wid)
        lines = [
            "type: tez-doktora" if row["Tür"].strip().lower().startswith("doktora") else "type: tez-yl",
            yaml_line("title", row["Tez Adı"].strip()),
            yaml_line("authors", [inverted(row["Yazar"])]),
            f"language: {language(row['Tez Adı'])}",
            *[yaml_line(k, v) for k, v in new_fields.items()],
            f"addedAt: {today}",
        ]
        if not dry:
            (OUT / f"{wid}.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
        report.append(f"NEW          {wid}  <=  {row['Tez Adı']}")
        added += 1

    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"{len(rows)} rows: {completed} existing records completed, {added} new records{' (dry run)' if dry else ''}")
    print(f"Report: {REPORT}")


if __name__ == "__main__":
    main()
