"""YÖK Ulusal Tez Merkezi'nden (tez.yok.gov.tr) doğrudan veri çekme.

Akış (tarayıcı gerekmez, düz HTTP):
  1. GET  tarama.jsp                → JSESSIONID çerezi + ABD listesi (ad → kod)
  2. POST SearchTez (form)          → sonuç listesi (en fazla 2000 satır)
  3. GET  tezBilgiDetay.jsp?...     → JSON: danışman, yer (üniv/enst/ABD/BD), özetler
  4. GET  getTezPdf.jsp?...         → PDF bağlantısı (TezGoster?key=...) veya kısıtlı

Önemli ayrıntılar (tezara.org'un açık kaynak tarayıcısından ve canlı testten):
  * islem=2, "-find"="  Bul", uni_group=on zorunlu; yoksa "Geçersiz sorgulama".
  * Durum=0 (Tümü) gönderilmeli; varsayılan 3 (Onaylandı) kayıtların ~%12'sini gizler.
  * Bir sorgu 2000'den fazla sonuç verirse yalnızca 2000'i gösterilir → sorgu
    yıl aralığı, tez türü ve dile bölünerek her parça 2000'in altına indirilir.
  * Kısa sürede çok sayıda ağır arama yapılırsa YÖK "TR7" başlıklı bir engel
    sayfası döndürür. Bu durumda uzun süre beklenir (varsayılan 30 dk, katlanarak).
"""
from __future__ import annotations

import json
import logging
import random
import re
import time
from dataclasses import dataclass
from datetime import date
from typing import Callable, Iterable

import httpx
from bs4 import BeautifulSoup

from .metin import clean_text, fold, title_case_tr

log = logging.getLogger("tezci.yok")

BASE = "https://tez.yok.gov.tr/UlusalTezMerkezi/"
UA = "Mozilla/5.0 (compatible; fikih-tez-arsivi/1.0; akademik arastirma)"

TUR_KODLARI = ["1", "2", "4", "3", "5", "6", "7"]  # YL, Doktora, Sanatta Yeterlik, uzmanlıklar
DIL_KODLARI = ["1", "2", "3", "4", "5", "6", "7"]


class YokEngeli(Exception):
    """YÖK geçici engel sayfası (TR7) veya bakım."""


class YokHatasi(Exception):
    pass


@dataclass
class Satir:
    id: int
    detail_id_1: str
    detail_id_2: str
    title_original: str
    title_translated: str
    author: str
    year: int | None
    thesis_type: str
    language: str
    subject_raw: str
    yer: str


# ---------------------------------------------------------------- ayrıştırma
def sayfa_turu(html: str) -> str:
    """'sonuc' | 'bos' | 'engel' | 'bakim' | 'hata'"""
    if re.search(r"<title>\s*TR7\s*</title>", html[:2000], re.I):
        return "engel"
    if re.search(r"BAKIM CALISMASI|undergoing maintenance", html, re.I):
        return "bakim"
    if re.search(r"Geçersiz sorgulama|tezSorguSonucHata", html, re.I):
        return "hata"
    if 'class="result-card' in html:
        return "sonuc"
    if 'result-count-text' in html or "kayıt bulunamadı" in html:
        return "bos"
    return "hata"


def sonuc_sayisi(html: str) -> tuple[int, int]:
    """'Arama sonucunda 2.572 kayıt bulundu. 2.000 tanesi görüntülenmektedir.' → (2572, 2000)"""
    m = re.search(r'<div class="result-count-text"[^>]*>([\s\S]*?)</div>', html)
    if not m:
        n = html.count('class="result-card')
        return n, n
    t = re.sub(r"<[^>]+>", " ", m.group(1))
    t = re.sub(r"\s+", " ", t)
    bul = re.search(r"([\d.]+)\s*kayıt bulundu", t)
    gos = re.search(r"([\d.]+)\s*tanesi", t)
    toplam = int(bul.group(1).replace(".", "")) if bul else 0
    gosterilen = int(gos.group(1).replace(".", "")) if gos else toplam
    return toplam, gosterilen


def _dengeli_nesne(src: str, bas: int) -> str | None:
    derinlik = 0
    for i in range(bas, len(src)):
        if src[i] == "{":
            derinlik += 1
        elif src[i] == "}":
            derinlik -= 1
            if derinlik == 0:
                return src[bas:i + 1]
    return None


def referans_verisi(html: str) -> dict:
    m = re.search(r"referenceData\s*=\s*\{", html)
    if not m:
        return {}
    blob = _dengeli_nesne(html, html.index("{", m.start()))
    if not blob:
        return {}
    try:
        return json.loads(re.sub(r",(\s*[}\]])", r"\1", blob))  # YÖK sondaki virgülleri bırakıyor
    except json.JSONDecodeError:
        return {}


def liste_ayristir(html: str) -> list[Satir]:
    soup = BeautifulSoup(html, "lxml" if _lxml_var() else "html.parser")
    ref = referans_verisi(html)
    satirlar: list[Satir] = []
    for kart in soup.select(".result-card"):
        idx = kart.get("data-index", "")
        meta = (ref.get(idx) or {}).get("meta") or {}
        m = re.search(r"Tez No:\s*(\d+)", kart.get_text(" "))
        k1, k2 = kart.get("data-kayitno"), kart.get("data-tezno")
        if not (m and k1 and k2):
            continue
        baslik = kart.select_one(".card-title")
        ceviri = kart.select_one(".title-container .card-info")
        yil = meta.get("year")
        satirlar.append(Satir(
            id=int(m.group(1)),
            detail_id_1=k1,
            detail_id_2=k2,
            title_original=clean_text(baslik.get_text(" ") if baslik else meta.get("title", "")),
            title_translated=clean_text(ceviri.get_text(" ")) if ceviri else "",
            author=clean_text(meta.get("author", "")),
            year=int(yil) if str(yil or "").isdigit() else None,
            thesis_type=clean_text(meta.get("type", "")),
            language=clean_text(meta.get("lang", "")),
            subject_raw=clean_text(meta.get("subject", "")),
            yer=clean_text(meta.get("yer", "")),
        ))
    return satirlar


def _lxml_var() -> bool:
    try:
        import lxml  # noqa: F401
        return True
    except ImportError:
        return False


def pdf_ayristir(html: str) -> tuple[str | None, bool]:
    m = re.search(r"href=['\"](TezGoster\?key=[^'\"]+)['\"]", html or "")
    if m:
        return BASE + m.group(1), False
    return None, bool(re.search(r"pdf-info-icon|togglePdfMsg|izinsiz", html or "", re.I))


def _birim_duzelt(s: str) -> str:
    s = title_case_tr(s.strip())
    s = re.sub(r"\bAnabilim Dalı\b", "Ana Bilim Dalı", s)
    s = re.sub(r"\((Disiplinlerarası)\)", lambda m: "(" + m.group(1).lower() + ")", s)
    return s


def yer_ayristir(yer: str) -> dict:
    """'İSTANBUL ÜNİVERSİTESİ / SOSYAL BİLİMLER ENSTİTÜSÜ / TEMEL İSLAM BİLİMLERİ ANABİLİM DALI / İslam Hukuku Bilim Dalı'"""
    parcalar = [p.strip() for p in (yer or "").split("/")]
    parcalar += [""] * (4 - len(parcalar))
    uni, ens, abd, bd = parcalar[:4]
    return {
        "university": title_case_tr(uni) if uni else "",
        "institute": title_case_tr(ens) if ens else "",
        "department": _birim_duzelt(abd) if abd else "",
        "branch": _birim_duzelt(bd) if bd else "",
    }


def ozet_ve_anahtar(metin: str | None) -> tuple[str, list[str]]:
    metin = clean_text(metin)
    m = re.search(r"(Anahtar\s+[Kk]elime(ler)?|Key\s*[Ww]ords?)\s*[:：]", metin)
    if not m:
        return metin, []
    ozet, satir = metin[:m.start()].strip(), metin[m.end():]
    kelimeler = [k.strip(" .;") for k in re.split(r"[;,]", satir) if k.strip(" .;")]
    return ozet, kelimeler[:25]


def danismanlar(s: str | None) -> list[str]:
    s = re.sub(r"<strong>.*?</strong>", "", s or "", flags=re.I | re.S)
    s = clean_text(s).replace("\n", ";")
    s = re.sub(r"^\s*(Eş\s*)?Danışman(lar)?\s*:\s*", "", s, flags=re.I)
    out = []
    for p in re.split(r";|\s{2,}", s):
        p = re.sub(r"^(Eş\s*)?Danışman\s*:\s*", "", p.strip(), flags=re.I)
        p = re.sub(r"^null\s+", "", p, flags=re.I)
        if p:
            out.append(p)
    return out


def tez_olustur(satir: Satir, detay: dict, pdf_html: str) -> dict:
    yer = yer_ayristir(detay.get("yer") or satir.yer)
    tr_ozet, tr_k = ozet_ve_anahtar(detay.get("trOzet"))
    en_ozet, en_k = ozet_ve_anahtar(detay.get("enOzet"))
    for alan, hedef in (("anahtarKelimeTr", tr_k), ("anahtarKelimeEn", en_k)):
        for k in re.split(r"[;,]", clean_text(detay.get(alan) or "")):
            k = k.strip(" .")
            if k and k not in hedef:
                hedef.append(k)
    pdf_url, kisitli = pdf_ayristir(pdf_html)
    return {
        "id": satir.id,
        "title_original": satir.title_original,
        "title_translated": satir.title_translated or None,
        "author": satir.author,
        "advisors": danismanlar(detay.get("danisman")),
        **yer,
        "detail_id_1": satir.detail_id_1,
        "detail_id_2": satir.detail_id_2,
        "year": satir.year,
        "thesis_type": satir.thesis_type,
        "language": satir.language,
        "subjects": [{"name": s.strip(), "language": "Turkish"} for s in satir.subject_raw.split(";") if s.strip()],
        "keywords": [{"name": k, "language": "Turkish"} for k in tr_k] + [{"name": k, "language": "English"} for k in en_k],
        "abstract_original": tr_ozet or None,
        "abstract_translated": en_ozet or None,
        "pdf_url": pdf_url,
        "restricted": kisitli,
    }


def satirdan_tez(satir: Satir) -> dict:
    """Detay çekilmeden, yalnız liste bilgisiyle ön sınıflandırma için."""
    return {
        "id": satir.id, "title_original": satir.title_original, "title_translated": satir.title_translated,
        "author": satir.author, "year": satir.year, "thesis_type": satir.thesis_type, "language": satir.language,
        "subjects": [{"name": s, "language": "Turkish"} for s in satir.subject_raw.split(";") if s],
        "keywords": [], "university": title_case_tr(satir.yer.split("/")[0].strip()) if satir.yer else "",
    }


# ---------------------------------------------------------------- oturum
def temel_form(**degis) -> dict:
    f = {
        "uniad": "", "Universite": "", "uni_yoksis_id": "", "source": "TR", "uni_group": "on",
        "ensad": "", "Enstitu": "0", "abdad": "", "ABD": "", "Konu": "",
        "Tur": "0", "Dil": "0", "izin": "0", "Durum": "0", "Bolum": "0",
        "yil1": "1", "yil2": "9999",
        "TezAd": "", "AdSoyad": "", "DanismanAdSoyad": "", "Dizin": "", "TezNo": "", "Metin": "",
        "islem": "2", "-find": "  Bul",
    }
    f.update({k: str(v) for k, v in degis.items()})
    return f


class YokOturum:
    def __init__(self, arama_bekleme: float = 30.0, detay_bekleme: float = 3.0,
                 engel_bekleme_dk: float = 30.0, engel_deneme: int = 3,
                 istemci: httpx.Client | None = None, uyku: Callable[[float], None] = time.sleep):
        self.arama_bekleme = arama_bekleme
        self.detay_bekleme = detay_bekleme
        self.engel_bekleme = engel_bekleme_dk * 60
        self.engel_deneme = engel_deneme
        self.uyku = uyku
        self.c = istemci or httpx.Client(
            base_url=BASE, timeout=180, follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9"},
        )
        self._son_arama = 0.0
        self._son_detay = 0.0
        self._acildi = False
        self.birimler: dict[str, str] = {}

    def _bekle(self, son: float, aralik: float) -> None:
        kalan = son + aralik * random.uniform(0.9, 1.3) - time.monotonic()
        if kalan > 0:
            self.uyku(kalan)

    def ac(self) -> None:
        r = self._istek("GET", "tarama.jsp")
        self.birimler = abd_listesi(r)
        self._acildi = True
        log.info("YÖK oturumu açıldı; %d ABD adı okundu", len(self.birimler))

    def _istek(self, yontem: str, yol: str, form: dict | None = None) -> str:
        for deneme in range(self.engel_deneme + 1):
            try:
                if yontem == "POST":
                    r = self.c.post(yol, data=form)
                else:
                    r = self.c.get(yol)
                metin = r.text
            except httpx.HTTPError as e:
                log.warning("Ağ hatası (%s): %s", yol, e)
                self.uyku(30 * (deneme + 1))
                continue
            tur = sayfa_turu(metin) if yontem == "POST" or yol == "tarama.jsp" else ("engel" if "<title>TR7" in metin[:500] else "ok")
            if tur in ("engel", "bakim"):
                bekle = self.engel_bekleme * (2 ** deneme)
                log.warning("YÖK %s sayfası döndürdü; %.0f dk bekleniyor (deneme %d/%d)",
                            tur.upper(), bekle / 60, deneme + 1, self.engel_deneme + 1)
                if deneme == self.engel_deneme:
                    break
                self.uyku(bekle)
                # Yeni oturum aç
                self.c.cookies.clear()
                try:
                    self.c.get("tarama.jsp")
                except httpx.HTTPError:
                    pass
                continue
            return metin
        raise YokEngeli(f"YÖK erişimi engellendi/bakımda: {yol}")

    def ara(self, **form) -> tuple[int, int, list[Satir]]:
        if not self._acildi:
            self.ac()
        self._bekle(self._son_arama, self.arama_bekleme)
        html = self._istek("POST", "SearchTez", temel_form(**form))
        self._son_arama = time.monotonic()
        tur = sayfa_turu(html)
        if tur == "bos":
            return 0, 0, []
        if tur == "hata":
            raise YokHatasi("YÖK sorguyu reddetti: " + json.dumps(form, ensure_ascii=False))
        toplam, gosterilen = sonuc_sayisi(html)
        return toplam, gosterilen, liste_ayristir(html)

    def detay(self, satir: Satir) -> dict:
        self._bekle(self._son_detay, self.detay_bekleme)
        govde = self._istek("GET", f"tezBilgiDetay.jsp?kayitNo={_q(satir.detail_id_1)}&tezNo={_q(satir.detail_id_2)}")
        self._son_detay = time.monotonic()
        try:
            detay = json.loads(govde.strip())
        except json.JSONDecodeError:
            detay = {}
        self._bekle(self._son_detay, self.detay_bekleme)
        pdf = self._istek("GET", f"getTezPdf.jsp?kayitNo={_q(satir.detail_id_1)}&tezNo={_q(satir.detail_id_2)}")
        self._son_detay = time.monotonic()
        return tez_olustur(satir, detay, pdf)

    def kapat(self):
        self.c.close()


def _q(s: str) -> str:
    from urllib.parse import quote
    return quote(s, safe="")


def abd_listesi(html: str) -> dict[str, str]:
    """tarama.jsp'deki ABD seçeneklerinden ad → kod sözlüğü."""
    out = {}
    for m in re.finditer(r'name="selected_abd"[^>]*?\bad="([^"]+)"[^>]*?\bkod="([^"]+)"', html):
        out[m.group(1)] = m.group(2)
    return out


# ---------------------------------------------------------------- bölerek arama
def bolerek_ara(oturum: YokOturum, taban: dict, yil1: int, yil2: int,
                geri_cagir: Callable[[dict, list[Satir]], None],
                tamam_mi: Callable[[dict], bool] = lambda p: False,
                limit: int = 2000) -> int:
    """Sorguyu 2000 sınırının altına inene dek yıl → tür → dil olarak böler.
    Her tamamlanan parça için geri_cagir(parametreler, satirlar) çağrılır."""
    toplam_satir = 0

    def calis(p: dict) -> None:
        nonlocal toplam_satir
        if tamam_mi(p):
            return
        toplam, gosterilen, satirlar = oturum.ara(**p)
        if toplam <= gosterilen or toplam < limit:
            geri_cagir(p, satirlar)
            toplam_satir += len(satirlar)
            return
        y1, y2 = int(p["yil1"]), int(p["yil2"])
        if y1 < y2:
            orta = (y1 + y2) // 2
            calis({**p, "yil1": y1, "yil2": orta})
            calis({**p, "yil1": orta + 1, "yil2": y2})
        elif p.get("Tur", "0") == "0":
            for t in TUR_KODLARI:
                calis({**p, "Tur": t})
        elif p.get("Dil", "0") == "0":
            for d in DIL_KODLARI:
                calis({**p, "Dil": d})
        else:
            log.warning("Sorgu bölünemedi, %d/%d satır alındı: %s", gosterilen, toplam, p)
            geri_cagir(p, satirlar)
            toplam_satir += len(satirlar)

    calis({**taban, "yil1": yil1, "yil2": yil2})
    return toplam_satir


def birimleri_sec(birimler: dict[str, str], desenler: Iterable[re.Pattern]) -> dict[str, str]:
    desenler = list(desenler)
    return {ad: kod for ad, kod in birimler.items() if any(d.search(fold(ad)) for d in desenler)}


def bu_yil() -> int:
    return date.today().year
