"""Dışa aktarma: Excel uyumlu CSV (İSNAD sütunlu), Zotero için RIS, web sitesi için JSON."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import isnad
from .metin import isnad_title, split_name, thesis_type_label, title_case_tr

TEZARA = "https://tezara.org/theses/{id}"


def _kw(t: dict, dil: str = "Turkish") -> list[str]:
    return [k["name"] for k in (t.get("keywords") or []) if k.get("language") == dil and k.get("name")]


def _danisman(t: dict) -> list[str]:
    return [title_case_tr(a).replace("Dr.", "Dr.") for a in (t.get("advisors") or [])]


def _kategori_adlari(t: dict, adlar: dict[str, str]) -> list[str]:
    return [adlar.get(k, k) for k in (t.get("kategoriler") or [])]


# ------------------------------------------------------------------ CSV
CSV_SUTUNLAR = [
    "Tez No", "Yazar", "Başlık", "Başlık (Çeviri)", "Tez Türü", "Yıl", "Üniversite", "Enstitü",
    "Ana Bilim Dalı", "Bilim Dalı", "Danışman", "Dil", "Anahtar Kelimeler", "Kategoriler",
    "Özet", "Özet (Çeviri)", "PDF", "Tez Sayfası", "İSNAD Kaynakça", "İSNAD Dipnot",
    "Durum", "Puan",
]


def csv_yaz(tezler: Iterable[dict], yol: Path, kategori_adlari: dict[str, str]) -> int:
    yol.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with yol.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_SUTUNLAR)
        for t in tezler:
            soyad, ad = split_name(t.get("author"))
            w.writerow([
                t["id"], f"{soyad}, {ad}".strip(", "), t.get("title_original") or "", t.get("title_translated") or "",
                thesis_type_label(t.get("thesis_type")), t.get("year") or "", t.get("university") or "",
                t.get("institute") or "", t.get("department") or "", t.get("branch") or "",
                "; ".join(_danisman(t)), t.get("language") or "", "; ".join(_kw(t)),
                "; ".join(_kategori_adlari(t, kategori_adlari)),
                t.get("abstract_original") or "", t.get("abstract_translated") or "",
                t.get("pdf_url") or ("(erişim kısıtlı)" if t.get("restricted") else ""),
                TEZARA.format(id=t["id"]), isnad.kaynakca(t), isnad.dipnot(t),
                t.get("durum") or "", t.get("puan") or "",
            ])
            n += 1
    return n


# ------------------------------------------------------------------ RIS (Zotero)
def _ris_satir(etiket: str, deger) -> str:
    deger = str(deger).replace("\r", " ").replace("\n", " ").strip()
    return f"{etiket}  - {deger}\n" if deger else ""


def ris_yaz(tezler: Iterable[dict], yol: Path, kategori_adlari: dict[str, str]) -> int:
    """Zotero: Dosya → İçe Aktar → bu .ris dosyası. İSNAD stili Zotero'da seçilir.

    Eşleme: TY THES · AU yazar · TI başlık · PY yıl · PB üniversite · CY şehir ·
    M3 tez türü · AB özet · KW anahtar kelime/kategori · UR PDF · LA dil ·
    AN Tez No · DB 'YÖK Ulusal Tez Merkezi' · N1 danışman, enstitü, ABD/BD.
    """
    yol.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with yol.open("w", encoding="utf-8") as f:
        for t in tezler:
            soyad, ad = split_name(t.get("author"))
            s = _ris_satir("TY", "THES")
            s += _ris_satir("AU", f"{soyad}, {ad}".strip(", "))
            for d in _danisman(t):
                s += _ris_satir("A3", d)  # Zotero: katkıda bulunan
            s += _ris_satir("TI", isnad_title(t.get("title_original")))
            if t.get("title_translated"):
                s += _ris_satir("TT", t["title_translated"])
            s += _ris_satir("PY", t.get("year") or "")
            s += _ris_satir("DA", t.get("year") or "")
            s += _ris_satir("PB", t.get("university") or "")
            s += _ris_satir("CY", isnad.sehir(t.get("university")))
            s += _ris_satir("M3", thesis_type_label(t.get("thesis_type")))
            s += _ris_satir("LA", t.get("language") or "")
            s += _ris_satir("AB", t.get("abstract_original") or "")
            for k in _kw(t):
                s += _ris_satir("KW", k)
            for k in _kategori_adlari(t, kategori_adlari):
                s += _ris_satir("KW", f"Kategori: {k}")
            s += _ris_satir("UR", t.get("pdf_url") or TEZARA.format(id=t["id"]))
            s += _ris_satir("AN", t["id"])
            s += _ris_satir("DB", "YÖK Ulusal Tez Merkezi")
            not_ = [f"Tez No: {t['id']}"]
            if t.get("institute"):
                not_.append(f"Enstitü: {t['institute']}")
            if t.get("department"):
                not_.append(f"ABD: {t['department']}")
            if t.get("branch"):
                not_.append(f"Bilim Dalı: {t['branch']}")
            if t.get("advisors"):
                not_.append("Danışman: " + "; ".join(_danisman(t)))
            s += _ris_satir("N1", " | ".join(not_))
            s += "ER  - \n\n"
            f.write(s)
            n += 1
    return n


# ------------------------------------------------------------------ JSON (site)
def site_kaydi(t: dict, kategori_adlari: dict[str, str]) -> dict:
    soyad, ad = split_name(t.get("author"))
    return {
        "id": t["id"],
        "baslik": t.get("title_original") or "",
        "baslik_isnad": isnad_title(t.get("title_original")),
        "baslik_ceviri": t.get("title_translated") or "",
        "yazar": {"ad": ad, "soyad": soyad},
        "danismanlar": _danisman(t),
        "tur": thesis_type_label(t.get("thesis_type")),
        "yil": t.get("year"),
        "universite": t.get("university") or "",
        "sehir": isnad.sehir(t.get("university")),
        "enstitu": t.get("institute") or "",
        "anabilim_dali": t.get("department") or "",
        "bilim_dali": t.get("branch") or "",
        "dil": t.get("language") or "",
        "konular": [s["name"] for s in (t.get("subjects") or []) if s.get("language") == "Turkish"],
        "anahtar_kelimeler": _kw(t),
        "anahtar_kelimeler_en": _kw(t, "English"),
        "ozet": t.get("abstract_original") or "",
        "ozet_ceviri": t.get("abstract_translated") or "",
        "pdf": t.get("pdf_url") or None,
        "pdf_kisitli": bool(t.get("restricted")),
        "tez_sayfasi": TEZARA.format(id=t["id"]),
        "kategoriler": t.get("kategoriler") or [],
        "kategori_adlari": _kategori_adlari(t, kategori_adlari),
        "isnad": {
            "kaynakca": isnad.kaynakca(t),
            "kaynakca_html": isnad.kaynakca(t, html=True),
            "dipnot": isnad.dipnot(t),
            "dipnot_html": isnad.dipnot(t, html=True),
            "kisa_dipnot": isnad.kisa_dipnot(t),
        },
        "eklenme": t.get("ilk_gorulme"),
        "guncelleme": t.get("son_guncelleme"),
    }


def site_yaz(tezler: list[dict], klasor: Path, kategori_adlari: dict[str, str]) -> int:
    klasor.mkdir(parents=True, exist_ok=True)
    kayitlar = [site_kaydi(t, kategori_adlari) for t in tezler]
    (klasor / "tezler.json").write_text(json.dumps(kayitlar, ensure_ascii=False, indent=0), encoding="utf-8")
    sayim: dict[str, int] = {k: 0 for k in kategori_adlari}
    yillar: dict[int, int] = {}
    for k in kayitlar:
        for c in k["kategoriler"]:
            sayim[c] = sayim.get(c, 0) + 1
        if k["yil"]:
            yillar[k["yil"]] = yillar.get(k["yil"], 0) + 1
    (klasor / "kategoriler.json").write_text(json.dumps(
        [{"anahtar": k, "ad": ad, "sayi": sayim.get(k, 0)} for k, ad in kategori_adlari.items()],
        ensure_ascii=False, indent=1), encoding="utf-8")
    (klasor / "meta.json").write_text(json.dumps({
        "olusturma": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "toplam": len(kayitlar),
        "yillar": dict(sorted(yillar.items())),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    # Son eklenenler (site ana sayfası için)
    son = sorted(kayitlar, key=lambda k: (k["eklenme"] or "", k["id"]), reverse=True)[:100]
    (klasor / "son_eklenenler.json").write_text(json.dumps(son, ensure_ascii=False, indent=0), encoding="utf-8")
    return len(kayitlar)


# ------------------------------------------------------------------ inceleme
INCELEME_SUTUNLAR = ["Tez No", "Karar (kabul/ret)", "Puan", "Başlık", "Ana Bilim Dalı", "Bilim Dalı",
                     "Üniversite", "Yıl", "Gerekçe", "Özet (ilk 400)", "Tez Sayfası"]


def inceleme_yaz(tezler: Iterable[dict], yol: Path) -> int:
    yol.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with yol.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(INCELEME_SUTUNLAR)
        for t in tezler:
            w.writerow([t["id"], "", t.get("puan"), t.get("title_original"), t.get("department"), t.get("branch"),
                        t.get("university"), t.get("year"), "; ".join(t.get("gerekce") or []),
                        (t.get("abstract_original") or "")[:400], TEZARA.format(id=t["id"])])
            n += 1
    return n


def inceleme_oku(yol: Path) -> list[tuple[int, str]]:
    kararlar = []
    with yol.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            k = (r.get("Karar (kabul/ret)") or r.get("Karar") or r.get("karar") or "").strip().lower()
            if not (r.get("Tez No") or r.get("id") or "").strip().isdigit():
                continue
            r["Tez No"] = (r.get("Tez No") or r.get("id")).strip()
            if k in ("kabul", "ret", "k", "r", "evet", "hayır", "hayir"):
                karar = "kabul" if k in ("kabul", "k", "evet") else "ret"
                kararlar.append((int(r["Tez No"]), karar))
    return kararlar
