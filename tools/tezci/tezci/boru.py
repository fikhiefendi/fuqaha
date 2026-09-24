"""Toplama hattı: kaynaklardan çek → kaydet → sınıflandır → (dışa aktar)."""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from . import disa_aktar
from .db import Depo
from .kaynak_tezara import TezaraIstemci, birim_seciciyi_olustur, normalize
from .kaynak_yok import (YokEngeli, YokOturum, birimleri_sec, bolerek_ara, satirdan_tez)
from .siniflandir import Siniflandirici, _compile

log = logging.getLogger("tezci")
KOK = Path(__file__).resolve().parent.parent


@dataclass
class Sayac:
    yeni: int = 0
    guncel: int = 0
    kabul: int = 0
    inceleme: int = 0
    atlanan: int = 0
    notlar: list[str] = field(default_factory=list)

    def ozet(self) -> str:
        return (f"yeni={self.yeni} güncellenen={self.guncel} kabul={self.kabul} "
                f"inceleme={self.inceleme} atlanan={self.atlanan}")


def ayarlari_yukle(yol: str | Path | None = None) -> dict:
    yol = Path(yol) if yol else KOK / "config" / "ayarlar.yaml"
    a = yaml.safe_load(yol.read_text(encoding="utf-8"))
    for anahtar in ("veritabani", "cikti_klasoru", "gunluk_dosyasi"):
        p = Path(a[anahtar])
        a[anahtar] = str(p if p.is_absolute() else KOK / p)
    return a


class Boru:
    def __init__(self, ayar: dict, sinif: Siniflandirici | None = None, depo: Depo | None = None,
                 tezara: TezaraIstemci | None = None, yok: YokOturum | None = None):
        self.a = ayar
        self.sinif = sinif or Siniflandirici()
        self.depo = depo or Depo(ayar["veritabani"])
        self._tezara = tezara
        self._yok = yok
        self.sayac = Sayac()

    # ---------------------------------------------------------------- ortak
    @property
    def tezara(self) -> TezaraIstemci:
        if self._tezara is None:
            t = self.a["tezara"]
            self._tezara = TezaraIstemci(t["url"], t["anahtar"], t.get("indeks", "theses"),
                                         t.get("sayfa_boyutu", 500), t.get("bekleme_sn", 1))
        return self._tezara

    @property
    def yok(self) -> YokOturum:
        if self._yok is None:
            y = self.a["yok"]
            self._yok = YokOturum(y["arama_bekleme_sn"], y["detay_bekleme_sn"], y["engel_bekleme_dk"], y["engel_deneme"])
        return self._yok

    def isle(self, tez: dict, kaynak: str, hepsini_sakla: bool = True) -> str:
        """Tezi sınıflandırır ve kaydeder. Döner: kabul | inceleme | ret"""
        s = self.sinif.siniflandir(tez)
        tur, _, _ = self.sinif.birim_turu(tez.get("department"), tez.get("branch"))
        if s.durum == "ret" and not hepsini_sakla and tur == "diger" and s.puan == 0:
            self.sayac.atlanan += 1
            return "ret"
        sonuc = self.depo.kaydet(tez, kaynak)
        self.depo.siniflandirma_yaz(tez["id"], s.durum, s.puan, s.kategoriler, s.gerekceler, self.sinif.surum)
        if sonuc == "yeni":
            self.sayac.yeni += 1
        else:
            self.sayac.guncel += 1
        if s.durum == "kabul":
            self.sayac.kabul += 1
        elif s.durum == "inceleme":
            self.sayac.inceleme += 1
        return s.durum

    # ---------------------------------------------------------------- tezara
    def _tezara_birimleri(self) -> dict:
        secici = birim_seciciyi_olustur(self.sinif)
        birimler = self.tezara.birimleri_kesfet(self.a["tezara"]["kesif_tohumlari"], secici)
        self.depo.bilgi_yaz("tezara_birimler", json.dumps(birimler, ensure_ascii=False))
        n_c = sum(1 for d in birimler.values() for t in d.values() if t == "cekirdek")
        n_g = sum(1 for d in birimler.values() for t in d.values() if t == "genis")
        log.info("tezara: %d çekirdek, %d geniş birim adı bulundu", n_c, n_g)
        return birimler

    def tezara_tara(self, anahtar_sorgular: bool = True) -> None:
        birimler = self._tezara_birimleri()
        filtre = TezaraIstemci.birim_filtresi(birimler, ("cekirdek", "genis"))
        en_buyuk = self.depo.en_buyuk_id()
        if filtre:
            anahtar = "tezara:birimler:" + hashlib.md5(filtre.encode()).hexdigest()[:12]
            if not self.depo.sorgu_tamam_mi(anahtar):
                n = 0
                for hit in self.tezara.bolerek_sayfala(filtre, 1900, date.today().year + 1):
                    self.isle(normalize(hit), "tezara")
                    en_buyuk = max(en_buyuk, hit["id"])
                    n += 1
                    if n % 1000 == 0:
                        self.depo.commit()
                        log.info("tezara birim taraması: %d kayıt işlendi (%s)", n, self.sayac.ozet())
                self.depo.sorgu_isaretle(anahtar, "tezara", {"filtre": filtre}, n)
        if anahtar_sorgular:
            ust = self.a["tezara"].get("anahtar_sorgu_ust_siniri", 3000)
            for q in self.sinif.ayar.get("anahtar_sorgular", []):
                anahtar = f"tezara:q:{q}"
                if self.depo.sorgu_tamam_mi(anahtar):
                    continue
                n = 0
                for hit in self.tezara.sayfala(q=q, ust_sinir=ust, matchingStrategy="all"):
                    self.isle(normalize(hit), "tezara", hepsini_sakla=False)
                    en_buyuk = max(en_buyuk, hit["id"])
                    n += 1
                self.depo.sorgu_isaretle(anahtar, "tezara", {"q": q}, n)
                log.info("tezara sorgu '%s': %d sonuç (%s)", q, n, self.sayac.ozet())
        self.depo.bilgi_yaz("tezara_son_id", str(en_buyuk))
        self.depo.bilgi_yaz("tezara_son_derin", _bugun())

    def tezara_guncelle(self, derin: bool = False) -> None:
        son_id = int(self.depo.bilgi_al("tezara_son_id") or self.depo.en_buyuk_id() or 0)
        log.info("tezara: Tez No > %d olan yeni kayıtlar çekiliyor", son_id)
        en_buyuk = son_id
        n = 0
        for hit in self.tezara.sayfala(f"id > {son_id}"):
            self.isle(normalize(hit), "tezara", hepsini_sakla=False)
            en_buyuk = max(en_buyuk, hit["id"])
            n += 1
            if n % 1000 == 0:
                self.depo.commit()
                self.depo.bilgi_yaz("tezara_son_id", str(en_buyuk))
        self.depo.bilgi_yaz("tezara_son_id", str(en_buyuk))
        log.info("tezara: %d yeni kayıt incelendi", n)

        son_derin = self.depo.bilgi_al("tezara_son_derin")
        gun = self.a["tezara"].get("derin_kontrol_gun", 30)
        if derin or not son_derin or _gun_farki(son_derin) >= gun:
            self.tezara_derin_kontrol()

    def tezara_derin_kontrol(self) -> None:
        """Birimlerdeki tüm Tez No'ları listeler; veritabanında olmayanları (geç eklenen
        eski tezler) çeker."""
        birimler = self._tezara_birimleri()
        filtre = TezaraIstemci.birim_filtresi(birimler, ("cekirdek", "genis"))
        if not filtre:
            return
        mevcut = self.depo.mevcut_idler()
        eksik = [h["id"] for h in self.tezara.sayfala(filtre, alanlar=["id"]) if h["id"] not in mevcut]
        log.info("tezara derin kontrol: %d eksik tez bulundu", len(eksik))
        for hit in self.tezara.idlerle_getir(eksik):
            self.isle(normalize(hit), "tezara")
        self.depo.bilgi_yaz("tezara_son_derin", _bugun())

    # ---------------------------------------------------------------- YÖK
    def yok_tara(self, yil1: int | None = None, yil2: int | None = None, isaretle: bool = True) -> None:
        y = self.a["yok"]
        yil1 = yil1 or y.get("en_eski_yil", 1950)
        yil2 = yil2 or date.today().year
        oturum = self.yok
        oturum.ac()
        desenler = [d for d, _ in self.sinif.cekirdek] + self.sinif.genis
        abdler = birimleri_sec(oturum.birimler, desenler)
        log.info("YÖK: %d ABD taranacak (%d–%d)", len(abdler), yil1, yil2)

        def tamam(p: dict) -> bool:
            return isaretle and self.depo.sorgu_tamam_mi(_anahtar(p))

        def geri(p: dict, satirlar, birim_turu: str):
            for satir in satirlar:
                if self.depo.detayli_mi(satir.id):
                    continue
                if birim_turu == "cekirdek" or (birim_turu == "genis" and y.get("genis_birim_detay", "hepsi") == "hepsi"):
                    tez = oturum.detay(satir)
                    self.isle(tez, "yok")
                else:
                    on = self.sinif.siniflandir(satirdan_tez(satir))
                    if on.puan >= self.sinif.inceleme_esigi:
                        self.isle(oturum.detay(satir), "yok", hepsini_sakla=False)
                    else:
                        self.sayac.atlanan += 1
            self.depo.commit()
            if isaretle:
                self.depo.sorgu_isaretle(_anahtar(p), "yok", p, len(satirlar))
            log.info("YÖK parça tamam %s → %d satır (%s)", _kisa(p), len(satirlar), self.sayac.ozet())

        try:
            for ad, kod in sorted(abdler.items()):
                tur, _, _ = self.sinif.birim_turu(ad, None)
                bolerek_ara(oturum, {"ABD": kod, "abdad": ad}, yil1, yil2,
                            lambda p, s, t=tur: geri(p, s, t), tamam)
            for q in self.sinif.ayar.get("anahtar_sorgular", []):
                for alan in ("TezAd", "Dizin"):
                    bolerek_ara(oturum, {alan: q}, yil1, yil2, lambda p, s: geri(p, s, "anahtar"), tamam)
        except YokEngeli as e:
            self.sayac.notlar.append(str(e))
            log.error("YÖK taraması durduruldu (sonraki çalıştırmada kaldığı yerden devam eder): %s", e)

    def yok_guncelle(self) -> None:
        geriye = self.a["yok"].get("guncelleme_geriye_yil", 1)
        yil = date.today().year
        self.yok_tara(yil - geriye, yil, isaretle=False)
        self.kisitli_pdf_kontrol()

    def kisitli_pdf_kontrol(self) -> None:
        gun = self.a["yok"].get("kisitli_pdf_kontrol_gun", 90)
        idler = self.depo.kisitli_eski(gun)
        if not idler:
            return
        from .kaynak_yok import pdf_ayristir, _q
        n = 0
        for tez_id in idler:
            r = self.depo.con.execute("SELECT detail_id_1, detail_id_2 FROM tezler WHERE id=?", (tez_id,)).fetchone()
            if not r or not r[0]:
                continue
            try:
                html = self.yok._istek("GET", f"getTezPdf.jsp?kayitNo={_q(r[0])}&tezNo={_q(r[1])}")
            except YokEngeli:
                break
            url, kisitli = pdf_ayristir(html)
            self.depo.con.execute(
                "UPDATE tezler SET pdf_url=COALESCE(?, pdf_url), restricted=?, son_guncelleme=datetime('now') WHERE id=?",
                (url, int(kisitli), tez_id))
            n += int(bool(url))
        self.depo.commit()
        log.info("PDF kontrolü: %d tezden %d tanesinin PDF'i artık erişilebilir", len(idler), n)

    # ---------------------------------------------------------------- diğer
    def ice_aktar_json(self, yol: Path) -> None:
        """tezara.org 'JSON İndir' çıktısını veya aynı şemadaki bir listeyi içe aktarır."""
        veri = json.loads(Path(yol).read_text(encoding="utf-8"))
        if isinstance(veri, dict):
            veri = veri.get("hits") or veri.get("theses") or []
        for hit in veri:
            self.isle(normalize(hit), "json")
        self.depo.commit()

    def alanlar_degistiyse_yeniden_siniflandir(self) -> None:
        """alanlar.yaml değiştiyse (ör. yeni terim eklendiyse) kayıtlı tüm tezleri yeniden sınıflandırır."""
        eski = self.depo.bilgi_al("alanlar_imza")
        if eski and eski != self.sinif.imza and self.depo.en_buyuk_id():
            log.info("alanlar.yaml değişmiş; tüm tezler yeniden sınıflandırılıyor: %s", self.yeniden_siniflandir())
        self.depo.bilgi_yaz("alanlar_imza", self.sinif.imza)

    def yeniden_siniflandir(self) -> dict:
        say = {"kabul": 0, "inceleme": 0, "ret": 0}
        for t in list(self.depo.tezler()):
            if t.get("manuel"):
                say[t["durum"]] = say.get(t["durum"], 0) + 1
                continue
            s = self.sinif.siniflandir(t)
            self.depo.siniflandirma_yaz(t["id"], s.durum, s.puan, s.kategoriler, s.gerekceler, self.sinif.surum)
            say[s.durum] += 1
        self.depo.commit()
        return say

    def disa_aktar(self, inceleme_dahil: bool | None = None) -> dict:
        if inceleme_dahil is None:
            inceleme_dahil = self.a.get("disa_aktar", {}).get("inceleme_dahil", False)
        durumlar = ["kabul", "inceleme"] if inceleme_dahil else ["kabul"]
        tezler = list(self.depo.tezler(durumlar))
        cikti = Path(self.a["cikti_klasoru"])
        adlar = self.sinif.kategori_adlari
        sonuc = {
            "csv": disa_aktar.csv_yaz(tezler, cikti / "fikih_tezleri.csv", adlar),
            "ris": disa_aktar.ris_yaz(tezler, cikti / "fikih_tezleri_zotero.ris", adlar),
            "site": disa_aktar.site_yaz(tezler, cikti / "site", adlar),
            "inceleme": disa_aktar.inceleme_yaz(self.depo.tezler(["inceleme"]), cikti / "incelenecek_tezler.csv"),
        }
        # Kategori başına ayrı RIS (Zotero'da ayrı koleksiyonlar için)
        for k in adlar:
            alt = [t for t in tezler if k in (t.get("kategoriler") or [])]
            disa_aktar.ris_yaz(alt, cikti / "zotero_kategoriler" / f"{k}.ris", adlar)
        return sonuc

    def siteye_aktar(self, site: str | Path | None = None, kuru: bool = False) -> dict:
        from . import siteye_aktar as sa
        sa_ayar = self.a.get("site") or {}
        site = Path(site or sa_ayar.get("klasor") or "")
        if not site or not str(site).strip():
            raise ValueError("Site klasörü belirtilmedi (ayarlar.yaml → site.klasor veya --site)")
        if not site.is_absolute():
            site = (KOK / site).resolve()
        kararlar = KOK / "kararlar.csv"
        if kararlar.exists():
            log.info("Elle kararlar uygulandı: %d", self.inceleme_yukle(kararlar))
        tezler = list(self.depo.tezler(["kabul"]))
        tezler.sort(key=lambda t: t["id"])
        ret = {r[0] for r in self.depo.con.execute("SELECT id FROM tezler WHERE durum='ret' AND manuel=1")}
        s = sa.aktar(tezler, site, sa_ayar.get("konu_eslemesi") or {}, sa_ayar.get("tur_duzelt", True), kuru,
                     cikarilacak=ret)
        if not kuru:
            disa_aktar.inceleme_yaz(self.depo.tezler(["inceleme"]), site / "sources" / "incelenecek-tezler.csv")
        return {"yeni": s.yeni, "tamamlanan": s.tamamlanan, "tur_duzeltilen": s.tur_duzeltilen,
                "cikarilan": s.cikarilan, "degismeyen": s.degismeyen}

    def inceleme_yukle(self, yol: Path) -> int:
        kararlar = disa_aktar.inceleme_oku(yol)
        for tez_id, karar in kararlar:
            r = self.depo.con.execute("SELECT * FROM tezler WHERE id=?", (tez_id,)).fetchone()
            if not r:
                continue
            from .db import satir_to_dict
            t = satir_to_dict(r)
            s = self.sinif.siniflandir(t)
            kats = s.kategoriler or (["fikih"] if karar == "kabul" else [])
            self.depo.siniflandirma_yaz(tez_id, karar, s.puan, kats if karar == "kabul" else [],
                                        s.gerekceler + ["elle karar"], self.sinif.surum, manuel=True, zorla=True)
        self.depo.commit()
        return len(kararlar)


def _anahtar(p: dict) -> str:
    return "yok:" + json.dumps(p, sort_keys=True, ensure_ascii=False)


def _kisa(p: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in p.items() if k in ("abdad", "TezAd", "Dizin", "yil1", "yil2", "Tur", "Dil"))


def _bugun() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _gun_farki(iso: str) -> int:
    try:
        return (datetime.now(timezone.utc).date() - date.fromisoformat(iso[:10])).days
    except ValueError:
        return 10 ** 6


__all__ = ["Boru", "ayarlari_yukle", "_compile"]
