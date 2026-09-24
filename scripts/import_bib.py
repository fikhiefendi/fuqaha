"""Import a Zotero BibTeX export into the bibliography (src/content/works/*.yaml).

Usage: python3 scripts/import_bib.py "path/to/export.bib" [--type tez-doktora]

- Local file attachments (Zotero `file` fields) are never copied.
- Personal reading tags (read, onemli) are dropped; other tags become topics.
- Existing records with the same id are overwritten, others are left alone.
"""
import json, re, sys, unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / "src/content/works"

TYPE_MAP = {"phdthesis": "tez-doktora", "mastersthesis": "tez-yl", "article": "makale", "book": "kitap",
            "incollection": "makale", "inproceedings": "bildiri"}
PRIVATE_TAGS = {"read", "onemli", "okunacak", "okundu"}
TOPICS = {
    "osmanli": "Osmanlı", "hanefilik": "Hanefîlik", "fikihtarihi": "Fıkıh tarihi", "literatur": "Literatür",
    "donem": "Dönem çalışmaları", "usul": "Fıkıh usulü", "fetva": "Fetva", "vakif": "Vakıf",
    "serhvehasiyeler": "Şerh ve hâşiyeler", "safiilik": "Şâfiîlik", "safii": "Şâfiîlik", "istibdal": "İstibdâl",
    "toprak": "Toprak hukuku", "tarihselcilik": "Tarihselcilik", "seyhulislam": "Şeyhülislamlık",
    "sahis": "Şahıs çalışmaları", "murabaha": "Murâbaha", "modern": "Modern dönem", "minkarizade": "Minkârîzâde",
    "mezheb": "Mezhep", "maveraunnehir": "Mâverâünnehir", "kavram": "Kavram çalışmaları", "istishab": "İstishâb",
    "istihsan": "İstihsân", "islamiktisadi": "İslam iktisadı", "ictihad": "İctihad", "horasan": "Horasan",
    "eyyubiler": "Eyyûbîler", "ekol": "Ekol", "edebulkadi": "Edebü'l-kâdî", "bagy": "Bağy", "akit": "Akit",
    "ahkam": "Ahkâm", "taskopruluzade": "Taşköprülüzâde",
}
EN_WORDS = re.compile(r"\b(the|of|and|in|on|for|an?|with|between|islamic|law)\b", re.I)


def parse(text: str):
    """Minimal brace-aware BibTeX reader: yields (entrytype, key, fields)."""
    i = 0
    while True:
        m = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,").search(text, i)
        if not m:
            return
        kind, key = m.group(1).lower(), m.group(2)
        i, fields = m.end(), {}
        while True:
            fm = re.compile(r"\s*(\w+)\s*=\s*").match(text, i)
            if not fm:
                break
            name, i = fm.group(1).lower(), fm.end()
            if text[i] == "{":
                depth, j = 0, i
                while True:
                    if text[j] == "{":
                        depth += 1
                    elif text[j] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                value, i = text[i + 1 : j], j + 1
            elif text[i] == '"':
                j = text.index('"', i + 1)
                value, i = text[i + 1 : j], j + 1
            else:
                vm = re.compile(r"[^,}\s]+").match(text, i)
                value, i = vm.group(0), vm.end()
            fields[name] = value
            cm = re.compile(r"\s*,").match(text, i)
            if cm:
                i = cm.end()
        yield kind, key, fields
        close = text.find("}", i)
        i = close + 1 if close != -1 else len(text)


def clean(s: str) -> str:
    s = s.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", s).strip()


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.replace("ı", "i").replace("İ", "i"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def language(title: str) -> str:
    if re.search(r"[؀-ۿ]", title):
        return "ar"
    if len(EN_WORDS.findall(title)) >= 2 and not re.search(r"[ıİşŞğĞçÇöÖüÜâîû]", title):
        return "en"
    return "tr"


def main():
    src = Path(sys.argv[1])
    force_type = sys.argv[sys.argv.index("--type") + 1] if "--type" in sys.argv else None
    OUT.mkdir(parents=True, exist_ok=True)
    added = date.today().isoformat()
    seen, count, skipped = set(), 0, 0
    for kind, key, f in parse(src.read_text(encoding="utf-8")):
        wtype = force_type or TYPE_MAP.get(kind)
        if not wtype or "title" not in f or "author" not in f:
            skipped += 1
            continue
        wid = slug(key)
        while wid in seen:
            wid += "-b"
        seen.add(wid)
        title = clean(f["title"])
        authors = [clean(a) for a in re.split(r"\s+and\s+", f["author"])]
        tags = [t.strip() for t in f.get("keywords", "").split(",") if t.strip()]
        topics = sorted({TOPICS.get(t.lower(), t) for t in tags if t.lower() not in PRIVATE_TAGS})
        lang = clean(f.get("language", "")) or language(title)
        lines = [
            f"type: {wtype}",
            f"title: {json.dumps(title, ensure_ascii=False)}",
            f"authors: {json.dumps(authors, ensure_ascii=False)}",
            f"language: {lang}",
        ]
        if f.get("year", "").strip().isdigit():
            lines.append(f"year: {int(f['year'])}")
        if f.get("school"):
            lines.append(f"university: {json.dumps(clean(f['school']), ensure_ascii=False)}")
        if f.get("address"):
            lines.append(f"city: {json.dumps(clean(f['address']), ensure_ascii=False)}")
        if f.get("publisher"):
            lines.append(f"publisher: {json.dumps(clean(f['publisher']), ensure_ascii=False)}")
        if f.get("journal"):
            lines.append(f"journal: {json.dumps(clean(f['journal']), ensure_ascii=False)}")
        if f.get("url"):
            lines.append(f"url: {json.dumps(f['url'].strip())}")
        if f.get("doi"):
            lines.append(f"doi: {json.dumps(f['doi'].strip())}")
        if topics:
            lines.append(f"topics: {json.dumps(topics, ensure_ascii=False)}")
        lines.append(f"addedAt: {added}")
        (OUT / f"{wid}.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
        count += 1
    print(f"{count} records written to {OUT}, {skipped} skipped")


if __name__ == "__main__":
    main()
