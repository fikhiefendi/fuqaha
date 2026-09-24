"""Print a range of parsed entries for reading: python3 scripts/show_batch.py 1 30"""
import json, sys
from pathlib import Path
entries = json.loads((Path(__file__).parent.parent / "sources/fawaid-entries.json").read_text())
a, b = int(sys.argv[1]), int(sys.argv[2])
for e in entries[a - 1 : b]:
    print(f"## {e['n']} [{e['pageStart']}-{e['pageEnd']}] {e['heading']}\n{e['text']}\n")
