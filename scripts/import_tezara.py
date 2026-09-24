"""Merge Tezara (tezara.org) thesis exports into the bibliography.

Usage: python3 scripts/import_tezara.py export1.json [export2.csv ...] [--dry-run]

Input: files saved with Tezara's "download" button (JSON or CSV), columns
"Tez No", "Başlık (Orijinal)", "Başlık (Çeviri)", "Özet (Orijinal)",
"Özet (Çeviri)", "Yazar", "Üniversite", "Enstitü", "Ana Bilim Dalı",
"Bilim Dalı", "Tez Türü", "Danışmanlar", "Yıl", "Safya Sayısı", "Dil", "PDF Linki".

Which theses are taken:
- every thesis of an Islamic law / Islamic economics department or branch
  (UNITS below), whatever its title;
- from any other department, a thesis whose title (original or translated)
  contains a term that is specific to fiqh, Islamic law or Islamic economics
  (TERMS). Words that are ambiguous on their own (kıyas, vakıf, kadı, miras…)
  count only next to a legal word.
Existing records are matched by Tezara number, then by author surname and title
(as in import_yok_csv.py) and only completed, never overwritten. Every decision
is written to sources/tezara-report.txt.
"""
import csv, json, re, sys, unicodedata
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from import_yok_csv import (  # noqa: E402
    OUT, clean_abstract, inverted, norm, person, read_works, same_thesis, slug, yaml_line,
)

ROOT = Path(__file__).parent.parent
REPORT = ROOT / "sources/tezara-report.txt"
EMPTY = "[[[[Yok]]]]"

UNITS = re.compile(
    r"^(islam hukuku|islam iktisadi ve hukuku|islam iktisadi|islam iktisadi ve finansi|islam iktisadi ve katilim bankaciligi|"
    r"islam ekonomisi ve finans|islam ekonomisi ve finansi|islam ekonomisi ve uluslararasi finans|islami bankacilik|"
    r"islami bankacilik ve finans|islami sigortacilik|fikih|fikih ve usulu|islam hukuku ve usulu)\b"
)

# Specific enough on their own (normalised, accent-free).
STRONG = [
    r"\bfik(i|ı)?h", r"\bfikh", r"\bfukaha", r"\bfakih", r"\bfetva", r"\bfetava", r"\bfeteva", r"\bmuftu", r"\bseyhulislam",
    r"\bislam hukuk", r"\bislami hukuk", r"\bser.?i hukuk", r"\bseriat", r"\bmecelle", r"\busul.?i fikih", r"\bfikih usul",
    r"\bhanefi", r"\bsafii", r"\bmaliki", r"\bhanbeli", r"\bcafer[iı] fikh", r"\bictihad", r"\bictihat", r"\bicma\b",
    r"\bistihsan", r"\bistislah", r"\bmaslahat", r"\bmakasid", r"\bseddu?.?z.?zeri", r"\bistishab", r"\bhiyel",
    r"\bislam ekonomi", r"\bislam iktisad", r"\bislami iktisat", r"\bislami ekonomi", r"\bislami finans", r"\bislami banka",
    r"\bkatilim banka", r"\bfaizsiz", r"\bsukuk", r"\bmurabaha", r"\bmudarebe", r"\bmusareke", r"\bmusaraka", r"\bicare\b",
    r"\btekaful", r"\bzekat", r"\bribah?\b", r"\bgarar\b", r"\bselem akdi", r"\bistisna akdi", r"\bhelal (gida|sertifika|urun|turizm)",
    r"\bislamic law", r"\bislamic jurisprudence", r"\bsharia", r"\bshari.?a\b", r"\bfiqh", r"\bfatwa", r"\bmufti", r"\busul al",
    r"\bislamic finance", r"\bislamic bank", r"\bislamic econom", r"\bparticipation bank", r"\binterest.free", r"\btakaful",
    r"\bhanafi", r"\bshafi", r"\bmaliki", r"\bhanbali", r"\bijtihad", r"\bmaqasid",
]
# Need a legal word nearby to count.
WEAK = [r"\bkiyas", r"\bvakif", r"\bvakf", r"\bkadi\b", r"\bkadilik", r"\bmiras", r"\bnikah", r"\btalak", r"\bbosanma",
        r"\bhad (ceza|suc)", r"\bkisas", r"\bdiyet\b", r"\btazir", r"\bmehir", r"\bnafaka", r"\bvasiyet", r"\bakit", r"\bakid\b",
        r"\bmezhep", r"\bmezheb", r"\bmuamelat", r"\bibadet", r"\bhukum", r"\bdelil", r"\bsicil"]
LEGAL = r"\b(hukuk|fikih|fikh|ser.?i|seriat|islam|mezhep|mezheb|fetva|kadi|law|legal|jurispr)"
ARABIC = re.compile(r"(الفقه|فقه|الفقهي|الشريعة|الشرعي|فتاوى|الفتوى|أصول الفقه|الإسلامي|المذهب الحنفي|الحنفية|الشافعية|المالكية|الحنابلة|الزكاة|المرابحة|الربا|الصكوك)")

LANG = {"türkçe": "tr", "arapça": "ar", "ingilizce": "en", "almanca": "de", "fransızca": "fr", "farsça": "fa", "rusça": "ru", "kürtçe": "ku", "azerice": "az"}
TYPE = {"doktora": "tez-doktora", "yüksek lisans": "tez-yl"}


def value(row, key):
    v = row.get(key)
    if v is None or v == EMPTY:
        return ""
    return str(v).strip()


def read_rows(paths):
    rows = []
    for p in paths:
        p = Path(p)
        if p.suffix.lower() == ".json":
            data = json.loads(p.read_text(encoding="utf-8"))
            rows += data if isinstance(data, list) else data.get("hits", [])
        else:
            rows += list(csv.DictReader(p.open(encoding="utf-8-sig")))
    seen, out = set(), []
    for r in rows:
        no = value(r, "Tez No")
        if no and no not in seen:
            seen.add(no)
            out.append(r)
    return out


def why_relevant(r):
    for unit in (value(r, "Bilim Dalı"), value(r, "Ana Bilim Dalı")):
        u = norm(unit).replace(" bilim dali", "").replace(" ana", "")
        if unit and UNITS.match(u):
            return f"unit: {unit}"
    title = " ".join(filter(None, [value(r, "Başlık (Orijinal)"), value(r, "Başlık (Çeviri)")]))
    t = norm(title)
    for p in STRONG:
        if re.search(p, t):
            return f"term: {p}"
    if ARABIC.search(title):
        return f"term: {ARABIC.search(title).group(0)}"
    if re.search(LEGAL, t):
        for p in WEAK:
            if re.search(p, t):
                return f"term+legal: {p}"
    return None


def fields(r, cities):
    uni = value(r, "Üniversite")
    inst = value(r, "Enstitü")
    dept = " / ".join(filter(None, [value(r, "Ana Bilim Dalı"), value(r, "Bilim Dalı")]))
    advisors = [person(a.strip()) if a.strip().isupper() else a.strip() for a in re.split(r",\s*", value(r, "Danışmanlar")) if a.strip()]
    translated = value(r, "Başlık (Çeviri)")
    out = {
        "year": int(value(r, "Yıl")) if value(r, "Yıl").isdigit() else None,
        "university": ", ".join(filter(None, [uni, inst])),
        "department": dept or None,
        "advisors": advisors or None,
        "pageCount": int(value(r, "Safya Sayısı")) if value(r, "Safya Sayısı").isdigit() else None,
        "url": f"https://tezara.org/theses/{value(r, 'Tez No')}",
        "fullText": value(r, "PDF Linki") or None,
        "abstract": clean_abstract(value(r, "Özet (Orijinal)")) or None,
        "abstractTranslation": clean_abstract(value(r, "Özet (Çeviri)")) or None,
        "titleTranslated": translated or None,
        "yokNo": int(value(r, "Tez No")) if value(r, "Tez No").isdigit() else None,
        "city": cities.get(uni),
    }
    return {k: v for k, v in out.items() if v}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    rows = read_rows(args)
    works = read_works()
    by_no = {}
    for w in works:
        m = re.search(r"^yokNo: (\d+)", w["text"], re.M)
        if m:
            by_no[m.group(1)] = w
    cities = {}
    for w in works:
        u = re.search(r'^university: "([^",]+)', w["text"], re.M)
        c = re.search(r"^city: (.*)$", w["text"], re.M)
        if u and c:
            cities.setdefault(u.group(1), json.loads(c.group(1)))

    report, skipped, completed, added = [], 0, 0, 0
    used = {w["id"] for w in works}
    today = date.today().isoformat()
    for r in rows:
        reason = why_relevant(r)
        title = value(r, "Başlık (Orijinal)")
        if not reason or not title:
            skipped += 1
            report.append(f"SKIP\t{value(r, 'Tez No')}\t{title}\t{value(r, 'Bilim Dalı') or value(r, 'Ana Bilim Dalı')}")
            continue
        f = fields(r, cities)
        ttype = TYPE.get(value(r, "Tez Türü").lower())
        if not ttype:
            skipped += 1
            report.append(f"SKIP-TYPE\t{value(r, 'Tez No')}\t{title}\t{value(r, 'Tez Türü')}")
            continue
        # The same thesis already in the archive?
        match = by_no.get(value(r, "Tez No"))
        if not match:
            surname = norm(value(r, "Yazar")).split()[-1] if value(r, "Yazar") else ""
            row_like = {"Tez Adı": title, "Yıl": value(r, "Yıl")}
            best = None
            for w in works:
                if surname and surname in w["surnames"]:
                    ok, ratio = same_thesis(row_like, w)
                    if ok and (best is None or ratio > best[1]):
                        best = (w, ratio)
            match = best[0] if best else None
        if match:
            missing = {k: v for k, v in f.items() if k not in match["keys"] and not (k == "url" and "url" in match["keys"])}
            report.append(f"MATCH\t{match['id']}\t{title}\t[+{', '.join(missing) or '—'}]")
            if missing:
                lines = match["text"].rstrip("\n").split("\n")
                at = next((i for i, l in enumerate(lines) if l.startswith("addedAt:")), len(lines))
                lines[at:at] = [yaml_line(k, v) for k, v in missing.items()]
                match["text"] = "\n".join(lines) + "\n"
                match["keys"] |= set(missing)
                if not dry:
                    match["path"].write_text(match["text"], encoding="utf-8")
                completed += 1
            continue
        author = value(r, "Yazar")
        words = [w for w in slug(title).split("-") if len(w) > 3][:2]
        wid = "-".join([slug(inverted(author).split(",")[0]) if author else "anon", *words, value(r, "Yıl") or "nodate"])
        while wid in used:
            wid += "-b"
        used.add(wid)
        lang = LANG.get(value(r, "Dil").lower(), "tr")
        lines = [
            f"type: {ttype}",
            yaml_line("title", title),
            yaml_line("authors", [inverted(author) if author.isupper() else author]),
            f"language: {lang}",
            *[yaml_line(k, v) for k, v in f.items()],
            f"addedAt: {today}",
        ]
        if not dry:
            (OUT / f"{wid}.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
        report.append(f"NEW\t{wid}\t{title}\t{reason}")
        added += 1

    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"{len(rows)} theses read: {added} new, {completed} existing completed, {skipped} not relevant{' (dry run)' if dry else ''}")
    print(f"Report: {REPORT}")


if __name__ == "__main__":
    main()
