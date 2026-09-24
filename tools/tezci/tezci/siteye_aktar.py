"""Kabul edilen tezleri Fuqaha sitesinin kaynakça koleksiyonuna (src/content/works/*.yaml) yazar.

Kurallar (sitenin scripts/import_yok_csv.py betiğiyle aynı ilke):
  * Sitede zaten bulunan bir kayıt YENİDEN YAZILMAZ; yalnızca eksik alanları eklenir.
  * Eşleşme sırası: yokId → YÖK bağlantısı (tezDetay id / TezGoster anahtarı) →
    yazar soyadı + başlık benzerliği.
  * Yeni tezler `origin: otomatik` işaretiyle yazılır; site bu kayıtlar için
    yalnızca Türkçe ayrıntı sayfası üretir (GitHub Pages boyut sınırı için).
  * Her karar sources/tezci-rapor.txt dosyasına yazılır.
"""
from __future__ import annotations

import difflib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable

from . import isnad
from .metin import clean_text, fold, isnad_title, split_name, title_case_tr

YOK = "https://tez.yok.gov.tr/UlusalTezMerkezi/"

DIL = {"turkce": "tr", "ingilizce": "en", "arapca": "ar", "almanca": "de", "fransizca": "fr",
       "farsca": "fa", "rusca": "ru", "ispanyolca": "es", "italyanca": "it", "urduca": "ur",
       "bosnakca": "bs", "azerice": "az", "kazakca": "kk", "ozbekce": "uz", "japonca": "ja"}

MEZHEP_KONU = [("hanefi", "Hanefîlik"), ("safii", "Şâfiîlik"), ("maliki", "Mâlikîlik"), ("hanbeli", "Hanbelîlik")]

UNVAN = re.compile(
    r"^(?:PROF(?:ESÖR|ESSOR)?|DOÇ(?:ENT)?|DOC|DR|YRD|YARD|ÖĞR|ÖĞRETİM|GÖR|ÜYESİ|ÜYE|ARŞ|ASSOC|ASSIST|ASST|UZM|"
    r"PROF\.DR|DOÇ\.DR|YRD\.DOÇ\.DR)\b\.?\s*", re.I)

STOP = set(
    "islam islami islamda hukuk hukuku hukukunda hukukuna hukukta hukuki fikih fikhi fikhinda fikhina fikhinin "
    "usul usulu usulunde usulunun ve ile bir bu da de icin olarak acisindan gore baglaminda cercevesinde "
    "ornegi orneginde uzerine hakkinda onun nin nun in un ser seri i l el er es en ed ibn b donem donemi "
    "anlayisi anlayis kavrami teorisi ilkesi hukumleri meselesi meseleleri incelemesi degerlendirme".split()
)


# ------------------------------------------------------------------ yardımcılar (import_yok_csv.py ile uyumlu)
def norm(s: str) -> str:
    s = (s or "").replace("ı", "i").replace("İ", "i").replace("I", "i")
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def anahtar_kelimeler(baslik: str) -> set[str]:
    return {w[:6] for w in norm(baslik).split() if len(w) > 3 and w not in STOP}


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.replace("ı", "i").replace("İ", "i"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def yaml_satir(anahtar: str, deger) -> str:
    if isinstance(deger, bool):
        return f"{anahtar}: {'true' if deger else 'false'}"
    if isinstance(deger, int):
        return f"{anahtar}: {deger}"
    return f"{anahtar}: {json.dumps(deger, ensure_ascii=False)}"


def danisman_adi(s: str) -> str:
    s = s.strip()
    for _ in range(6):
        yeni = UNVAN.sub("", s).strip(" .,")
        if yeni == s:
            break
        s = yeni
    return " ".join("-".join(title_case_tr(p) for p in w.split("-")) for w in s.split())


def dil_kodu(dil: str | None, baslik: str) -> str:
    kod = DIL.get(fold(dil).replace(" ", ""))
    if kod:
        return kod
    if re.search(r"[؀-ۿ]", baslik or ""):
        return "ar"
    return "tr"


# ------------------------------------------------------------------ mevcut kayıtlar
@dataclass
class Kayit:
    id: str
    yol: Path
    metin: str
    baslik: str
    soyadlar: set[str]
    yil: int | None
    anahtarlar: set[str]
    yok_id: int | None
    baglanti: set[str] = field(default_factory=set)


def _alan(metin: str, k: str):
    m = re.search(rf"^{k}: (.*)$", metin, re.M)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return m.group(1).strip()


def mevcutlari_oku(klasor: Path) -> list[Kayit]:
    out = []
    for f in sorted(klasor.glob("*.yaml")):
        t = f.read_text(encoding="utf-8")
        yazarlar = _alan(t, "authors") or []
        baglanti = set()
        for k in ("url", "fullText"):
            v = _alan(t, k) or ""
            m = re.search(r"(?:tezDetay\.jsp\?id=|TezGoster\?key=)([^&\s\"]+)", v)
            if m:
                baglanti.add(m.group(1))
        yok_id = _alan(t, "yokId")
        out.append(Kayit(
            id=f.stem, yol=f, metin=t, baslik=_alan(t, "title") or "",
            soyadlar={norm(a.split(",")[0]).split()[-1] for a in yazarlar if norm(a)},
            yil=_alan(t, "year") if isinstance(_alan(t, "year"), int) else None,
            anahtarlar=set(re.findall(r"^(\w+):", t, re.M)),
            yok_id=int(yok_id) if str(yok_id or "").isdigit() else None,
            baglanti=baglanti,
        ))
    return out


def ayni_tez(baslik: str, yil: int | None, k: Kayit) -> tuple[bool, float]:
    oran = difflib.SequenceMatcher(None, norm(baslik), norm(k.baslik)).ratio()
    yillar_uyar = k.yil is None or yil is None or k.yil == yil
    if oran >= 0.8 and (yillar_uyar or abs((k.yil or 0) - (yil or 0)) <= 1):
        return True, oran
    ortak = anahtar_kelimeler(baslik) & anahtar_kelimeler(k.baslik)
    return bool(ortak) and yillar_uyar and oran >= 0.45, oran


# ------------------------------------------------------------------ alan üretimi
def site_alanlari(t: dict, konu_eslemesi: dict[str, str]) -> dict:
    soyad, ad = split_name(t.get("author"))
    tur = fold(t.get("thesis_type"))
    baslik = isnad_title(t.get("title_original"))
    ceviri = (t.get("title_translated") or "").strip()
    dil = dil_kodu(t.get("language"), t.get("title_original") or "")
    alan: dict = {
        "type": "tez-yl" if "yuksek lisans" in tur else "tez-doktora",
        "title": baslik,
    }
    if ceviri:
        hedef = "tr" if dil != "tr" and re.search(r"[çğıöşüÇĞİÖŞÜ]", ceviri) else ("en" if dil != "en" else "tr")
        alan["titleTranslation"] = {hedef: ceviri}
    alan["authors"] = [f"{soyad}, {ad}".strip(", ")]
    alan["language"] = dil
    if t.get("year"):
        alan["year"] = int(t["year"])
    uni = ", ".join(x for x in [t.get("university"), t.get("institute")] if x)
    if uni:
        alan["university"] = uni
    sehir = isnad.sehir(t.get("university"))
    if sehir:
        alan["city"] = sehir
    birim = " / ".join(x for x in [t.get("department"), t.get("branch")] if x)
    if birim:
        alan["department"] = birim
    dan = [danisman_adi(a) for a in (t.get("advisors") or []) if a and a.strip()]
    if dan:
        alan["advisors"] = dan
    konular = [konu_eslemesi[k] for k in (t.get("kategoriler") or []) if konu_eslemesi.get(k)]
    fb = fold(t.get("title_original"))
    for anahtar, konu in MEZHEP_KONU:
        if re.search(r"\b" + anahtar, fb) and konu not in konular:
            konular.append(konu)
    if konular:
        alan["topics"] = list(dict.fromkeys(konular))
    if t.get("detail_id_1"):
        alan["url"] = f"{YOK}tezDetay.jsp?id={t['detail_id_1']}"
    if t.get("pdf_url"):
        alan["fullText"] = t["pdf_url"]
    ozet = clean_text(t.get("abstract_original")).replace("\n", " ")
    if ozet:
        alan["abstract"] = re.sub(r"\s{2,}", " ", ozet)
    alan["yokId"] = int(t["id"])
    return alan


# ------------------------------------------------------------------ ana işlem
@dataclass
class Sonuc:
    yeni: int = 0
    tamamlanan: int = 0
    tur_duzeltilen: int = 0
    degismeyen: int = 0
    cikarilan: int = 0
    rapor: list[str] = field(default_factory=list)


def aktar(tezler: Iterable[dict], site: Path, konu_eslemesi: dict[str, str],
          tur_duzelt: bool = True, kuru: bool = False, bugun: str | None = None,
          cikarilacak: set[int] | None = None) -> Sonuc:
    klasor = site / "src" / "content" / "works"
    if not klasor.is_dir():
        raise FileNotFoundError(f"Site klasörü bulunamadı: {klasor}")
    bugun = bugun or date.today().isoformat()
    kayitlar = mevcutlari_oku(klasor)
    yok_idx = {k.yok_id: k for k in kayitlar if k.yok_id}
    bag_idx = {b: k for k in kayitlar for b in k.baglanti}
    soyad_idx: dict[str, list[Kayit]] = {}
    for k in kayitlar:
        for s in k.soyadlar:
            soyad_idx.setdefault(s, []).append(k)
    kullanilan = {k.id for k in kayitlar}
    sonuc = Sonuc()

    # Elle "ret" kararı verilen tezler: yalnızca otomatik eklenmiş kayıtlar silinir.
    for yok_id in sorted(cikarilacak or ()):
        k = yok_idx.get(yok_id)
        if k and re.search(r"^origin: otomatik$", k.metin, re.M):
            if not kuru:
                k.yol.unlink()
            sonuc.cikarilan += 1
            sonuc.rapor.append(f"ÇIKARILDI {k.id} (elle ret) <= {yok_id}")
            del yok_idx[yok_id]

    for t in tezler:
        alan = site_alanlari(t, konu_eslemesi)
        # 1) kesin eşleşme
        k = yok_idx.get(alan["yokId"])
        kesin = k is not None
        if not k:
            for b in (t.get("detail_id_1"), _anahtar(t.get("pdf_url"))):
                if b and b in bag_idx:
                    k, kesin = bag_idx[b], True
                    break
        # 2) bulanık eşleşme
        oran = 1.0
        if not k:
            soyad = norm(split_name(t.get("author"))[0]).split()[-1:] or [""]
            en_iyi = None
            for aday in soyad_idx.get(soyad[0], []):
                ok, r = ayni_tez(alan["title"], alan.get("year"), aday)
                if ok and (en_iyi is None or r > en_iyi[1]):
                    en_iyi = (aday, r)
            if en_iyi:
                k, oran = en_iyi

        if k:
            eksik = {a: v for a, v in alan.items() if a not in k.anahtarlar and a not in ("type", "title", "authors", "language")}
            satirlar = k.metin.rstrip("\n").split("\n")
            not_ = []
            if tur_duzelt and kesin and "type" in k.anahtarlar:
                eski = _alan(k.metin, "type")
                if eski in ("tez-doktora", "tez-yl") and eski != alan["type"]:
                    satirlar = [yaml_satir("type", alan["type"]) if s.startswith("type:") else s for s in satirlar]
                    not_.append(f"tür {eski}→{alan['type']}")
                    sonuc.tur_duzeltilen += 1
            if eksik:
                at = next((i for i, s in enumerate(satirlar) if s.startswith("addedAt:")), len(satirlar))
                satirlar[at:at] = [yaml_satir(a, v) for a, v in eksik.items()]
            if eksik or not_:
                yeni_metin = "\n".join(satirlar) + "\n"
                if not kuru:
                    k.yol.write_text(yeni_metin, encoding="utf-8")
                k.metin = yeni_metin
                k.anahtarlar |= set(eksik)
                if eksik:
                    sonuc.tamamlanan += 1
                sonuc.rapor.append(f"TAMAMLANDI {oran:.2f} {k.id} <= {t['id']} [+{', '.join(eksik) or '—'}{'; ' + '; '.join(not_) if not_ else ''}]")
            else:
                sonuc.degismeyen += 1
            yok_idx[alan["yokId"]] = k
            continue

        # 3) yeni kayıt
        soyad_slug = slug(alan["authors"][0].split(",")[0]) or "yazar"
        kelimeler = [w for w in slug(alan["title"]).split("-") if len(w) > 3][:2]
        wid = "-".join([soyad_slug, *kelimeler, str(alan.get("year") or "nodate")])
        while wid in kullanilan:
            wid += "-b"
        kullanilan.add(wid)
        satirlar = [yaml_satir(a, v) for a, v in alan.items()]
        satirlar += ["origin: otomatik", f"addedAt: {bugun}"]
        yol = klasor / f"{wid}.yaml"
        if not kuru:
            yol.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
        yeni = Kayit(id=wid, yol=yol, metin="\n".join(satirlar), baslik=alan["title"],
                     soyadlar={norm(alan["authors"][0].split(",")[0]).split()[-1]} if norm(alan["authors"][0]) else set(),
                     yil=alan.get("year"), anahtarlar=set(alan) | {"origin", "addedAt"}, yok_id=alan["yokId"])
        yok_idx[alan["yokId"]] = yeni
        for s in yeni.soyadlar:
            soyad_idx.setdefault(s, []).append(yeni)
        sonuc.yeni += 1
        sonuc.rapor.append(f"YENİ {wid} <= {t['id']} {alan['title'][:90]}")

    rapor = site / "sources" / "tezci-rapor.txt"
    if not kuru:
        rapor.parent.mkdir(parents=True, exist_ok=True)
        rapor.write_text(
            f"# {bugun}: {sonuc.yeni} yeni, {sonuc.tamamlanan} tamamlandı, {sonuc.tur_duzeltilen} tür düzeltildi, "
            f"{sonuc.cikarilan} çıkarıldı, {sonuc.degismeyen} değişmedi\n" + "\n".join(sonuc.rapor) + "\n", encoding="utf-8")
    return sonuc


def _anahtar(pdf: str | None) -> str | None:
    m = re.search(r"TezGoster\?key=([^&\s]+)", pdf or "")
    return m.group(1) if m else None
