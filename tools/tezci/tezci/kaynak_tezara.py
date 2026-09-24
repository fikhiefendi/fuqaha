"""tezara.org arama altyapısından (Meilisearch) veri çekme — hızlı yol.

tezara.org, YÖK verisini sürekli tarayıp temizleyen açık kaynaklı (MIT) bir projedir
ve arama sonuçlarının toplu indirilmesine izin verir. Sitenin tarayıcıda kullandığı
yalnızca-arama (search-only) anahtarı herkese açıktır; değişirse config.yaml'dan
güncelleyin. Bu kaynak üçüncü taraf bir projeye bağlı olduğundan sistem YÖK'ten
doğrudan çekmeyi de destekler (kaynak_yok.py).

Kullanılan Meilisearch özellikleri (canlı test edildi):
  * filter: department / branch / id / year alanlarında süzme
  * sort: id:asc
  * facet-search: ABD ve bilim dalı adlarını bulmak için
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Iterator

import httpx

from .metin import fold

log = logging.getLogger("tezci.tezara")

TUM_ALANLAR = None  # attributesToRetrieve verilmezse hepsi gelir


def _tirnak(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


class TezaraIstemci:
    def __init__(self, url: str, anahtar: str, indeks: str = "theses", sayfa: int = 500,
                 bekleme: float = 1.0, istemci: httpx.Client | None = None,
                 uyku: Callable[[float], None] = time.sleep):
        self.url = url.rstrip("/")
        self.indeks = indeks
        self.sayfa = sayfa
        self.bekleme = bekleme
        self.uyku = uyku
        self.c = istemci or httpx.Client(
            timeout=180,
            headers={"Authorization": f"Bearer {anahtar}", "Content-Type": "application/json",
                     "User-Agent": "fikih-tez-arsivi/1.0"},
        )

    def _post(self, yol: str, govde: dict) -> dict:
        for deneme in range(5):
            try:
                r = self.c.post(f"{self.url}/indexes/{self.indeks}/{yol}", json=govde)
                if r.status_code == 429 or r.status_code >= 500:
                    raise httpx.HTTPStatusError("sunucu", request=r.request, response=r)
                r.raise_for_status()
                self.uyku(self.bekleme)
                return r.json()
            except httpx.HTTPStatusError as e:
                if e.response is not None and e.response.status_code in (401, 403):
                    raise RuntimeError("tezara anahtarı geçersiz; config.yaml → tezara.anahtar değerini güncelleyin") from e
                log.warning("tezara hatası (%s), tekrar denenecek: %s", yol, e)
            except httpx.HTTPError as e:
                log.warning("tezara ağ hatası (%s): %s", yol, e)
            self.uyku(10 * (deneme + 1))
        raise RuntimeError(f"tezara'ya ulaşılamadı: {yol}")

    # ------------------------------------------------------------------
    def toplam(self, filtre: str = "", q: str = "", **ek) -> int:
        d = self._post("search", {"q": q, "filter": filtre, "hitsPerPage": 1, "page": 1,
                                  "attributesToRetrieve": ["id"], **ek})
        return int(d.get("totalHits") or d.get("estimatedTotalHits") or 0)

    def sayfala(self, filtre: str = "", q: str = "", ust_sinir: int | None = None,
                alanlar: list[str] | None = TUM_ALANLAR, **ek) -> Iterator[dict]:
        sayfa, gelen = 1, 0
        while True:
            govde = {"q": q, "filter": filtre, "hitsPerPage": self.sayfa, "page": sayfa, "sort": ["id:asc"], **ek}
            if q:
                govde.pop("sort")  # metin aramasında alaka sıralaması
            if alanlar:
                govde["attributesToRetrieve"] = alanlar
            d = self._post("search", govde)
            hits = d.get("hits") or []
            for h in hits:
                yield h
                gelen += 1
                if ust_sinir and gelen >= ust_sinir:
                    return
            toplam_sayfa = d.get("totalPages") or 0
            if not hits or sayfa >= toplam_sayfa:
                return
            sayfa += 1

    def bolerek_sayfala(self, filtre: str, yil1: int, yil2: int, esik: int = 9000) -> Iterator[dict]:
        """Sonuç sayısı sunucunun sayfalama sınırını aşarsa yıl aralığına bölerek çeker."""
        f = f"({filtre}) AND year >= {yil1} AND year <= {yil2}"
        n = self.toplam(f)
        if n == 0:
            return
        if n > esik and yil1 < yil2:
            orta = (yil1 + yil2) // 2
            yield from self.bolerek_sayfala(filtre, yil1, orta, esik)
            yield from self.bolerek_sayfala(filtre, orta + 1, yil2, esik)
            return
        yield from self.sayfala(f)

    def faset_ara(self, alan: str, sorgu: str) -> list[tuple[str, int]]:
        d = self._post("facet-search", {"facetName": alan, "facetQuery": sorgu})
        return [(h["value"], h["count"]) for h in d.get("facetHits", [])]

    def birimleri_kesfet(self, tohumlar: list[str], secici: Callable[[str], str]) -> dict[str, dict[str, str]]:
        """ABD/BD adlarını facet-search ile bulur ve secici(ad) ile ('cekirdek'|'genis'|'diger') etiketler."""
        sonuc: dict[str, dict[str, str]] = {"department": {}, "branch": {}}
        for alan in ("department", "branch"):
            for t in tohumlar:
                for ad, _ in self.faset_ara(alan, t):
                    tur = secici(ad)
                    if tur != "diger":
                        sonuc[alan][ad] = tur
        return sonuc

    @staticmethod
    def birim_filtresi(birimler: dict[str, dict[str, str]], turler: tuple[str, ...]) -> str:
        parcalar = []
        for alan in ("department", "branch"):
            adlar = [a for a, t in birimler[alan].items() if t in turler]
            if adlar:
                parcalar.append(f"{alan} IN [{', '.join(_tirnak(a) for a in sorted(adlar))}]")
        return " OR ".join(parcalar)

    def idlerle_getir(self, idler: list[int], parca: int = 200) -> Iterator[dict]:
        for i in range(0, len(idler), parca):
            grup = idler[i:i + parca]
            yield from self.sayfala(f"id IN [{', '.join(map(str, grup))}]")


def birim_seciciyi_olustur(siniflandirici) -> Callable[[str], str]:
    def secici(ad: str) -> str:
        tur, _, _ = siniflandirici.birim_turu(ad, None)
        return tur
    return secici


def normalize(hit: dict) -> dict:
    """tezara kaydı zaten YÖK tarayıcısının şemasıyla aynıdır; küçük temizlik."""
    t = dict(hit)
    t.pop("_formatted", None)
    t["advisors"] = t.get("advisors") or []
    t["subjects"] = t.get("subjects") or []
    t["keywords"] = t.get("keywords") or []
    return t


FOLD = fold  # dışa açık
