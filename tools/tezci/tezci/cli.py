"""Komut satırı.

  python -m tezci tara                 # ilk (tam) tarama — mevcut tüm tezler
  python -m tezci guncelle             # yeni eklenen tezler (haftalık zamanlanır)
  python -m tezci calistir             # guncelle + disa-aktar (zamanlayıcı bunu çağırır)
  python -m tezci disa-aktar           # CSV + Zotero RIS + site JSON üret
  python -m tezci siteye-aktar         # kabul edilenleri Fuqaha sitesine (src/content/works) yaz
  python -m tezci durum                # sayılar
  python -m tezci yeniden-siniflandir  # alanlar.yaml değişince
  python -m tezci inceleme-yukle cikti/incelenecek_tezler.csv
  python -m tezci ice-aktar-json dosya.json   # tezara.org 'JSON İndir' çıktısı
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .boru import Boru, ayarlari_yukle


def _gunluk(yol: str, ayrintili: bool) -> None:
    Path(yol).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if ayrintili else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(yol, encoding="utf-8")],
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _kaynaklar(secim: str) -> list[str]:
    return ["tezara", "yok"] if secim == "ikisi" else [secim]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tezci", description="Fıkıh / İslam hukuku / İslam iktisadı tez arşivi")
    ap.add_argument("--ayar", help="ayarlar.yaml yolu")
    ap.add_argument("--alanlar", help="alanlar.yaml yolu")
    ap.add_argument("-v", "--ayrintili", action="store_true")
    alt = ap.add_subparsers(dest="komut", required=True)

    p = alt.add_parser("tara", help="ilk/tam tarama")
    p.add_argument("--kaynak", choices=["tezara", "yok", "ikisi"])
    p.add_argument("--yil1", type=int)
    p.add_argument("--yil2", type=int)
    p.add_argument("--sifirla", action="store_true", help="tamamlanmış sorgu kayıtlarını silip baştan tara")

    p = alt.add_parser("guncelle", help="yeni tezleri çek")
    p.add_argument("--kaynak", choices=["tezara", "yok", "ikisi"])
    p.add_argument("--derin", action="store_true", help="birimlerin tamamını eksik tez için kontrol et")

    p = alt.add_parser("calistir", help="guncelle + disa-aktar (zamanlayıcı için)")
    p.add_argument("--kaynak", choices=["tezara", "yok", "ikisi"])

    p = alt.add_parser("siteye-aktar", help="kabul edilen tezleri Fuqaha sitesine yaz")
    p.add_argument("--site", help="site deposunun klasörü (varsayılan: ayarlar.yaml → site.klasor)")
    p.add_argument("--kuru", action="store_true", help="dosya yazmadan ne olacağını göster")

    p = alt.add_parser("disa-aktar")
    p.add_argument("--inceleme-dahil", action="store_true")

    alt.add_parser("durum")
    alt.add_parser("yeniden-siniflandir")
    p = alt.add_parser("inceleme-yukle")
    p.add_argument("dosya")
    p = alt.add_parser("ice-aktar-json")
    p.add_argument("dosya")

    a = ap.parse_args(argv)
    ayar = ayarlari_yukle(a.ayar)
    _gunluk(ayar["gunluk_dosyasi"], a.ayrintili)
    log = logging.getLogger("tezci")

    from .siniflandir import Siniflandirici
    boru = Boru(ayar, Siniflandirici(a.alanlar))
    cid = boru.depo.calisma_baslat(" ".join(argv or sys.argv[1:]))
    try:
        if a.komut in ("tara", "guncelle", "calistir", "siteye-aktar"):
            boru.alanlar_degistiyse_yeniden_siniflandir()
        if a.komut == "tara":
            if a.sifirla:
                boru.depo.sorgulari_sifirla()
            for k in _kaynaklar(a.kaynak or ayar["kaynak"]):
                if k == "tezara":
                    boru.tezara_tara()
                else:
                    boru.yok_tara(a.yil1, a.yil2)
        elif a.komut in ("guncelle", "calistir"):
            for k in _kaynaklar(a.kaynak or ayar["kaynak"]):
                try:
                    if k == "tezara":
                        boru.tezara_guncelle(derin=getattr(a, "derin", False))
                    else:
                        boru.yok_guncelle()
                except Exception as e:  # bir kaynak çökerse diğeri yine çalışsın
                    log.exception("%s kaynağında hata: %s", k, e)
                    boru.sayac.notlar.append(f"{k}: {e}")
            if a.komut == "calistir":
                log.info("Dışa aktarıldı: %s", boru.disa_aktar())
                if (ayar.get("site") or {}).get("klasor"):
                    log.info("Siteye aktarıldı: %s", boru.siteye_aktar())
        elif a.komut == "siteye-aktar":
            log.info("Siteye aktarıldı: %s", boru.siteye_aktar(a.site, a.kuru))
        elif a.komut == "disa-aktar":
            log.info("Dışa aktarıldı: %s", boru.disa_aktar(a.inceleme_dahil or None))
        elif a.komut == "yeniden-siniflandir":
            log.info("Yeniden sınıflandırıldı: %s", boru.yeniden_siniflandir())
        elif a.komut == "inceleme-yukle":
            log.info("%d elle karar işlendi", boru.inceleme_yukle(Path(a.dosya)))
        elif a.komut == "ice-aktar-json":
            boru.ice_aktar_json(Path(a.dosya))
        elif a.komut == "durum":
            print(json.dumps(boru.depo.istatistik(), ensure_ascii=False, indent=2))
        log.info("Bitti: %s", boru.sayac.ozet())
        return 0
    finally:
        boru.depo.calisma_bitir(cid, boru.sayac.yeni, boru.sayac.guncel, boru.sayac.kabul,
                                "; ".join(boru.sayac.notlar))
        boru.depo.close()


if __name__ == "__main__":
    raise SystemExit(main())
