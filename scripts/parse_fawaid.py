"""Split al-Laknawī's al-Fawāʾid al-bahiyya (OpenITI text) into biography entries.

Output: sources/fawaid-entries.json — one object per entry with the heading,
the cleaned Arabic text, and the printed-edition pages it spans.
The digital text states that its page numbers match the printed edition.
"""
import json, re, sys
from pathlib import Path

SRC = Path(__file__).parent.parent / "sources" / "fawaid-bahiyya.txt"
OUT = SRC.with_name("fawaid-entries.json")

raw = SRC.read_text(encoding="utf-8-sig")
body = raw.split("#META#Header#End#", 1)[1]

PAGE = re.compile(r"PageV(\d+)P(\d+)")
MS = re.compile(r"\s*ms\d+\s*")
FOOTNOTE_MARK = re.compile(r"\s*\(¬\d+\)")

entries, section, current = [], None, None
page = 1  # page markers close a page, so text before the first marker is on p. 1


def clean(line: str) -> str:
    line = re.sub(r"^(#|~~)\s*", "", line)
    line = MS.sub(" ", line)
    line = FOOTNOTE_MARK.sub("", line)
    return line


for line in body.splitlines():
    if line.startswith("### |"):
        title = line.lstrip("#| ").strip()
        section = title
        if current:
            entries.append(current)
            current = None
        if "الخاتمة" in title:
            break
        continue
    if line.startswith("### $"):
        if current:
            entries.append(current)
        heading = FOOTNOTE_MARK.sub("", line[5:]).strip()
        current = {"n": len(entries) + 1, "section": section, "heading": heading, "pageStart": page, "text": ""}
        # A heading line may carry the first words of the entry.
        rest = PAGE.split(heading)
        continue
    if current is None:
        for m in PAGE.finditer(line):
            page = int(m.group(2)) + 1
        continue
    parts = PAGE.split(line)
    # parts: text, vol, page, text, vol, page, text...
    current["text"] += " " + clean(parts[0]).strip()
    for i in range(1, len(parts), 3):
        page = int(parts[i + 1]) + 1
        current["text"] += f" \u27e6{page}\u27e7 " + clean(parts[i + 2]).strip()

if current:
    entries.append(current)

# Some biographies were not given their own heading in the digital text; they
# start inside the previous entry. Split them out (suffix b, c, …).
INLINE = {
    111: [r"\(الحسن بن أبي مالك\)"],
    159: [r"\(زيرك محمد\)"],
    191: [r"\[[^\]]{2,40}\]"],
    511: [r"يوسف القره صوي"],
}
# The last entry is followed by the author's closing note, which is not part of it.
CLOSING = "* هذا آخر ما لخصته"
BREAK = re.compile(r"\u27e6(\d+)\u27e7")


def finish(e):
    """Resolve page markers into a page range and clean the text."""
    text = e["text"]
    pages = [int(m) for m in BREAK.findall(text)]
    # A marker at the very end means the entry ended on the previous page.
    stripped = text.rstrip()
    trailing = BREAK.search(stripped) and BREAK.findall(stripped)[-1] and stripped.endswith("\u27e7")
    e["pageEnd"] = max([e["pageStart"]] + [p for p in pages]) - (1 if trailing else 0)
    e["pageEnd"] = max(e["pageEnd"], e["pageStart"])
    e["text"] = re.sub(r"\s+", " ", BREAK.sub(" ", text)).strip()
    e["heading"] = PAGE.sub("", MS.sub(" ", e["heading"])).strip()
    return e


for e in entries:
    if CLOSING in e["text"]:
        e["text"] = e["text"].split(CLOSING)[0]

out = []
for e in entries:
    pats = INLINE.get(e["n"])
    if not pats:
        out.append(finish(e))
        continue
    rx = re.compile("|".join(pats))
    pieces, last, heads = [], 0, []
    for m in rx.finditer(e["text"]):
        pieces.append(e["text"][last : m.start()])
        heads.append(m.group(0))
        last = m.end()
    pieces.append(e["text"][last:])
    first = dict(e, text=pieces[0])
    out.append(finish(first))
    page = e["pageStart"]
    for p in BREAK.findall(pieces[0]):
        page = int(p)
    for k, (head, body) in enumerate(zip(heads, pieces[1:])):
        # Heading words that follow the bracket (e.g. "بن محمد ...:") belong to the heading line.
        sub = {"n": f"{e['n']}{chr(ord('b') + k)}", "section": e["section"], "heading": head,
               "pageStart": page, "text": body}
        out.append(finish(sub))
        for p in BREAK.findall(body):
            page = int(p)
entries = out

OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(entries), "entries →", OUT)
