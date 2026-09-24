"""Match our places to the al-Thurayya gazetteer (CC BY 4.0) by Arabic name + distance.

Writes sources/thurayya-matches.json: {place_id: {uri, lat, lng, name, dist_km}}.
Places with no match within MAX_KM keep their own approximate coordinates.
"""
import json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from places import PLACES  # noqa: E402

MAX_KM = 150
# Where our Arabic label differs from the gazetteer's headword.
ALIASES = {
    "medine": ["يثرب", "المدينة"], "mekke": ["مكة"], "istanbul": ["القسطنطينية", "قسطنطينية"],
    "fustat": ["فسطاط", "مصر"], "harezm": ["الجرجانية", "جرجانية", "كركانج"], "fergana": ["اخسيكث", "أخسيكث"],
    "taberistan": ["آمل", "امل"], "kirim": ["القرم", "صلغات", "سلغات"], "sistan": ["زرنج"],
    "kumis": ["سمنان"], "sas": ["الشاش", "بنكث", "تاشكند"], "farab": ["فاراب", "اترار"],
    "usrusene": ["بونجكث", "بنجكث"], "ezriat": ["أذرعات", "اذرعات"], "curcan": ["جرجان"],
    "kudus": ["بيت المقدس", "إيلياء", "ايلياء"], "tebriz": ["تبريز"], "cam": ["جام", "بوزجان"],
    "kesaniye": ["كشانية", "الكشانية", "كشاني"], "sugd": ["الصغد", "السغد", "صغد"],
    "medain": ["المدائين"], "malatya": ["ملطين"], "berdaa": ["برذعة"], "ramhurmuz": ["رام هرمز"],
    "kirman": ["بردسير"], "esterabad": ["أستارباذ"], "velvalic": ["ورواليج"], "damgan": ["الدمغان"],
    "buhara": ["بخارة"], "tirmiz": ["الترميذ"], "mergilan": ["مرغينن"], "ahlat": ["أخلاط"],
}


def norm(s: str) -> str:
    s = re.sub(r"[ً-ْٰ]", "", s)
    s = re.sub(r"[أإآٱ]", "ا", s).replace("ة", "ه").replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"^ال", "", s.strip())
    return re.sub(r"\s+", " ", s)


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def main():
    feats = json.loads((ROOT / "sources/althurayya-places.geojson").read_text())["features"]
    index = {}
    for f in feats:
        c = f["properties"]["cornuData"]
        names = {c.get("toponym_arabic", ""), *str(c.get("toponym_arabic_other", "")).split(",")}
        lon, lat = f["geometry"]["coordinates"]
        for n in names:
            if n.strip():
                index.setdefault(norm(n), []).append((lat, lon, c))
    out, missing = {}, []
    for pid, (tr, en, ar, region, lat, lng) in PLACES.items():
        keys = [norm(ar.split("(")[0])] + [norm(a) for a in ALIASES.get(pid, [])]
        cands = [x for k in keys for x in index.get(k, [])]
        rank = lambda x: km((lat, lng), x[:2]) + (60 if x[2].get("top_type_hom") == "regions" else 0)
        best = min(cands, key=rank, default=None)
        if best and km((lat, lng), best[:2]) <= MAX_KM:
            out[pid] = {"uri": best[2]["cornu_URI"], "lat": round(best[0], 5), "lng": round(best[1], 5),
                        "name": best[2]["toponym_translit"], "dist_km": round(km((lat, lng), best[:2]))}
        else:
            missing.append(pid)
    (ROOT / "sources/thurayya-matches.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(len(out), "matched;", len(missing), "not in gazetteer:", missing)
    far = {k: v["dist_km"] for k, v in out.items() if v["dist_km"] > 40}
    print("moved >40 km:", far)


if __name__ == "__main__":
    main()
