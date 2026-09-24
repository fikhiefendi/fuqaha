"""Tezleri alan tanımlarına (config/alanlar.yaml) göre puanlar ve kategorilere ayırır.

Sonuç: durum ∈ {kabul, inceleme, ret}, puan, kategoriler, gerekçeler.
Kural tabanlıdır ve açıklanabilirdir: her kararın gerekçesi kayda geçer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .metin import fold

VARSAYILAN_AYAR = Path(__file__).resolve().parent.parent / "config" / "alanlar.yaml"


def _compile(term: str) -> re.Pattern:
    if term.startswith("re:"):
        return re.compile(term[3:])
    return re.compile(r"(?<![\w])" + re.escape(fold(term)))


def _as_list(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


@dataclass
class Terim:
    ham: str
    desen: re.Pattern
    agirlik: int
    kategoriler: list[str]
    baglam: bool
    guclu: bool = True


@dataclass
class Sonuc:
    durum: str
    puan: int
    kategoriler: list[str] = field(default_factory=list)
    gerekceler: list[str] = field(default_factory=list)


class Siniflandirici:
    def __init__(self, ayar_yolu: str | Path | None = None):
        yol = Path(ayar_yolu) if ayar_yolu else VARSAYILAN_AYAR
        metin = yol.read_text(encoding="utf-8")
        self.ayar: dict[str, Any] = yaml.safe_load(metin)
        import hashlib
        self.imza = hashlib.sha1(metin.encode("utf-8")).hexdigest()[:12]
        a = self.ayar
        self.surum = a.get("surum", 1)
        self.cekirdek = [(_compile(x["desen"]), _as_list(x["kategori"])) for x in a["cekirdek_birimler"]]
        self.genis = [_compile(x) for x in a["genis_birimler"]]
        self.kategori_adlari: dict[str, str] = a["kategoriler"]
        p = a["puanlama"]
        self.carpan = p["carpan"]
        self.ozet_ust = p["ozet_ust_sinir"]
        self.kabul_esigi = p["kabul_esigi"]
        self.inceleme_esigi = p["inceleme_esigi"]
        self.diger_dal_esigi = p.get("diger_dal_kabul_esigi", self.kabul_esigi)
        self.genel_dallar = [fold(x) for x in p.get("genel_dallar", [])]
        self.guclu_sart = bool(p.get("diger_bolumde_guclu_sinyal_sart", False))
        self.terimler = [
            Terim(x["t"], _compile(x["t"]), int(x["a"]), _as_list(x.get("k")), bool(x.get("baglam")),
                  bool(x.get("guclu", not x.get("baglam"))))
            for x in a["terimler"]
        ]
        self.baglam = [_compile(x) for x in a["islami_baglam"]]
        self.dislama = sorted((fold(x) for x in a.get("dislama_ifadeleri", [])), key=len, reverse=True)
        self.fukaha_adlari = [_compile(x) for x in a.get("fukaha_adlari", [])]
        self.fukaha_kaliplari = [_compile(x) for x in a.get("fukaha_kaliplari", [])]
        self.tarih_kaliplari = [_compile(x) for x in a.get("tarih_kaliplari", [])]

    # ------------------------------------------------------------------
    def birim_turu(self, department: str | None, branch: str | None) -> tuple[str, list[str], str]:
        """('cekirdek'|'genis'|'diger', kategoriler, eşleşen birim)"""
        for alan in (branch, department):
            f = fold(alan)
            if not f:
                continue
            for desen, kats in self.cekirdek:
                if desen.search(f):
                    return "cekirdek", kats, alan or ""
        for alan in (department, branch):
            f = fold(alan)
            if f and any(d.search(f) for d in self.genis):
                return "genis", [], alan or ""
        return "diger", [], ""

    def _temizle(self, s: str) -> str:
        f = fold(s)
        for x in self.dislama:
            f = f.replace(x, " ")
        return f

    def siniflandir(self, t: dict) -> Sonuc:
        tur, cek_kat, birim = self.birim_turu(t.get("department"), t.get("branch"))

        baslik = self._temizle(" | ".join(filter(None, [t.get("title_original"), t.get("title_translated")])))
        anahtar = self._temizle(" | ".join(k["name"] for k in (t.get("keywords") or []) if k.get("name")))
        ozet = self._temizle(" ".join(filter(None, [t.get("abstract_original"), t.get("abstract_translated")]))[:6000])
        hepsi = " ".join([baslik, anahtar, ozet])

        baglam_var = tur in ("cekirdek", "genis") or any(b.search(hepsi) for b in self.baglam)

        puan = 0
        guclu = False
        ozet_puan = 0
        kat_puan: dict[str, int] = {}
        gerekce: list[str] = []
        for terim in self.terimler:
            if terim.baglam and not baglam_var:
                continue
            for alan, metin in (("baslik", baslik), ("anahtar", anahtar), ("ozet", ozet)):
                if not metin or not terim.desen.search(metin):
                    continue
                p = terim.agirlik * self.carpan[alan]
                if alan == "ozet" and p > 0:
                    p = min(p, max(0, self.ozet_ust - ozet_puan))
                    ozet_puan += p
                if p == 0:
                    continue
                puan += p
                if terim.guclu and terim.agirlik >= 2:
                    guclu = True
                for k in terim.kategoriler:
                    kat_puan[k] = kat_puan.get(k, 0) + p
                gerekce.append(f"{alan}:{terim.ham}(+{p})")
                break  # aynı terim en güçlü alanından bir kez sayılır

        esik = self.kabul_esigi
        if tur == "genis":
            genel = lambda x: any(g in x for g in self.genel_dallar)
            abd, dal = fold(t.get("department")), fold(t.get("branch"))
            if not ((not abd or genel(abd)) and (not dal or genel(dal))):
                esik = max(esik, self.diger_dal_esigi)
        if tur == "cekirdek":
            durum = "kabul"
            gerekce.insert(0, f"çekirdek birim: {birim}")
            puan = max(puan, 100)
        elif puan >= esik:
            durum = "kabul"
        elif puan >= self.inceleme_esigi:
            durum = "inceleme"
        else:
            durum = "ret"
        if durum == "kabul" and tur == "diger" and self.guclu_sart and not guclu:
            durum = "inceleme"
            gerekce.append("güçlü sinyal yok → inceleme")

        kategoriler: list[str] = []
        if durum != "ret":
            kategoriler = self._kategoriler(tur, cek_kat, kat_puan, baslik, ozet)
        return Sonuc(durum=durum, puan=puan, kategoriler=kategoriler, gerekceler=gerekce[:12])

    def _kategoriler(self, tur, cek_kat, kat_puan, baslik, ozet) -> list[str]:
        kats: list[str] = list(cek_kat)
        # Terimlerden gelen kategoriler: anlamlı puanı olanlar
        for k, p in sorted(kat_puan.items(), key=lambda x: -x[1]):
            if p >= 3 and k not in kats:
                kats.append(k)
        fikih_sinyali = any(k in kat_puan for k in ("fikih", "fikih_usulu", "fukaha")) or "fikih" in cek_kat
        # Fukahâ: başlıkta fakih adı veya "görüşleri/tahkik/eserleri" kalıbı
        if fikih_sinyali or tur == "cekirdek":
            if any(d.search(baslik) for d in self.fukaha_adlari) or (
                any(d.search(baslik) for d in self.fukaha_kaliplari) and ("fukaha" in kat_puan or "fikih" in kat_puan or tur == "cekirdek")
            ):
                if "fukaha" not in kats:
                    kats.append("fukaha")
            if any(d.search(baslik) for d in self.tarih_kaliplari) and "fikih_tarihi" not in kats:
                kats.append("fikih_tarihi")
        # Her kabul edilen tezin en az bir ana kategorisi olsun
        if not kats:
            kats = ["fikih"]
        if "iktisat" not in kats and any(k in kats for k in ("fikih_usulu", "fikih_tarihi", "fukaha", "mukayeseli")) and "fikih" not in kats:
            kats.insert(0, "fikih")
        # Bilinmeyen anahtarları at
        return [k for k in dict.fromkeys(kats) if k in self.kategori_adlari]
