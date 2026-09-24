import json
from pathlib import Path

import httpx
import pytest

from tezci import isnad
from tezci.boru import Boru, ayarlari_yukle
from tezci.db import Depo
from tezci.kaynak_tezara import TezaraIstemci
from tezci.kaynak_yok import (YokEngeli, YokOturum, abd_listesi, bolerek_ara, danismanlar, liste_ayristir,
                              ozet_ve_anahtar, pdf_ayristir, sayfa_turu, sonuc_sayisi, yer_ayristir)
from tezci.metin import fold, isnad_title, split_name
from tezci.siniflandir import Siniflandirici

FX = Path(__file__).parent / "fixtures"
S = Siniflandirici()


def fx(ad):
    return (FX / ad).read_text(encoding="utf-8")


# ------------------------------------------------------------ metin
def test_fold():
    assert fold("FIKHÎ") == "fikhi"
    assert fold("Şer‘iyye Sicilleri") == "seriyye sicilleri"
    assert fold("İSLÂM") == "islam"


def test_isnad_title():
    assert isnad_title("Ürdün Fetva Dairesi ve tıbbi fetvalarının mukayeseli analizi") == \
        "Ürdün Fetva Dairesi ve Tıbbi Fetvalarının Mukayeseli Analizi"
    assert isnad_title("SERAHSÎ'NİN EL-MEBSÛT'UNDA İSTİHSAN") == "Serahsî'nin el-Mebsût'unda İstihsan"
    assert isnad_title("ibn Teymiyye ile ibn Kayyim: bir mukayese") .startswith("İbn Teymiyye ile İbn Kayyim: Bir")


def test_split_name():
    assert split_name("ALİ İHSAN PALA") == ("Pala", "Ali İhsan")
    assert split_name("MEHMET BOYNUKALIN") == ("Boynukalın", "Mehmet")


# ------------------------------------------------------------ YÖK ayrıştırma
def test_yok_liste():
    html = fx("yok_liste.html")
    assert sayfa_turu(html) == "sonuc"
    assert sonuc_sayisi(html) == (2, 2)
    rows = liste_ayristir(html)
    assert [r.id for r in rows] == [1012137, 1012200]
    r = rows[0]
    assert r.author == "AYŞENUR EROL" and r.year == 2024 and r.thesis_type == "Yüksek Lisans"
    assert r.title_translated.startswith("Comparative analysis")
    assert r.detail_id_1 == "4ieE6xjHHiuCq81TZgVWpQ"


def test_yok_sayi_kesilmis():
    h = '<div class="result-count-text"> Arama sonucunda 2.572 kayıt bulundu. 2.000 tanesi görüntülenmektedir. </div><div class="result-card"'
    assert sonuc_sayisi(h) == (2572, 2000)


def test_yok_engel():
    assert sayfa_turu(fx("yok_engel.html")) == "engel"


def test_yok_detay_pdf():
    d = json.loads(fx("yok_detay.json").strip())
    y = yer_ayristir(d["yer"])
    assert y == {"university": "İstanbul Üniversitesi", "institute": "Sosyal Bilimler Enstitüsü",
                 "department": "Temel İslam Bilimleri Ana Bilim Dalı", "branch": "İslam Hukuku Bilim Dalı"}
    ozet, kw = ozet_ve_anahtar(d["trOzet"])
    assert kw == ["Fetva", "Kolektif içtihat", "Biyofıkıh"] and "Anahtar" not in ozet
    assert danismanlar(d["danisman"]) == ["DOÇ. DR. MERVE ÖZAYKAL"]
    url, kisitli = pdf_ayristir(fx("yok_pdf.html"))
    assert url.endswith("TezGoster?key=5T1_CZ5-UGb9QCmoURec4FnDkx4ZvZDoVScSSgXD_aKRQmGPsvl61ybbAc5iyvPs") and not kisitli


def test_abd_listesi():
    b = abd_listesi(fx("yok_tarama.html"))
    assert b["İSLAM HUKUKU ANABİLİM DALI"] == "860"
    assert len(b) == 5


# ------------------------------------------------------------ sınıflandırma
def T(title, dept="", branch="", kw=(), abstract="", te=""):
    return {"title_original": title, "title_translated": te, "department": dept, "branch": branch,
            "keywords": [{"name": k, "language": "Turkish"} for k in kw], "abstract_original": abstract}


@pytest.mark.parametrize("tez,durum,kat", [
    (T("Emrin yorumu", "Temel İslam Bilimleri Ana Bilim Dalı", "İslam Hukuku Bilim Dalı"), "kabul", "fikih"),
    (T("Katılım bankalarında risk yönetimi", "İslam Ekonomisi ve Finansı Ana Bilim Dalı"), "kabul", "iktisat"),
    (T("Serahsî'nin fıkıh usulündeki görüşleri", "Temel İslam Bilimleri Ana Bilim Dalı", "Tefsir Bilim Dalı"), "kabul", "fukaha"),
    (T("İslam hukuku ile Türk Medeni Kanunu'nda nafaka: karşılaştırmalı bir inceleme", "Özel Hukuk Ana Bilim Dalı"), "kabul", "mukayeseli"),
    (T("Osmanlı'da şer'iyye sicillerine göre kadı mahkemeleri", "Tarih Ana Bilim Dalı"), "inceleme", "fikih_tarihi"),
    (T("Şer'iyye sicillerine göre Osmanlı'da fıkhî uygulamalar", "Tarih Ana Bilim Dalı"), "kabul", "fikih_tarihi"),
    (T("Faizsiz bankacılık ve sukuk ihracı", "İşletme Ana Bilim Dalı"), "kabul", "iktisat"),
    (T("Hanefi mezhebinde istihsan delili", "Felsefe ve Din Bilimleri Ana Bilim Dalı"), "kabul", "fikih_usulu"),
])
def test_kabul(tez, durum, kat):
    s = S.siniflandir(tez)
    assert s.durum == durum, s
    assert kat in s.kategoriler, s


@pytest.mark.parametrize("tez", [
    T("Faiz oranlarının enflasyon üzerindeki etkisi", "İktisat Ana Bilim Dalı"),
    T("Kadın girişimcilerin finansmana erişimi", "İşletme Ana Bilim Dalı"),
    T("Vakıf üniversitelerinde öğrenci memnuniyeti", "Eğitim Bilimleri Ana Bilim Dalı"),
    T("Kültürel miras alanlarında turizm", "Turizm Ana Bilim Dalı"),
    T("Akdeniz bölgesinde iklim değişikliği", "Coğrafya Ana Bilim Dalı"),
    T("Hükümet sistemleri ve anayasa", "Kamu Hukuku Ana Bilim Dalı"),
    T("Kısas-ı Enbiya'da Hz. Musa kıssası", "Temel İslam Bilimleri Ana Bilim Dalı", "Tefsir Bilim Dalı"),
    T("Diyet uygulamalarının obezite üzerine etkisi", "Beslenme Ana Bilim Dalı"),
    T("Türk vergi yargısında kıyas yasağı ilkesi", "Maliye Ana Bilim Dalı"),
    T("Kepçe dişleri için kıyas yolu ile malzeme geliştirme", "Makine Mühendisliği Ana Bilim Dalı"),
    T("Tahâvî akâidi'nin Mâtürîdîlik açısından değerlendirilmesi", "Temel İslam Bilimleri Ana Bilim Dalı"),
])
def test_ret(tez):
    s = S.siniflandir(tez)
    assert s.durum == "ret", s


def test_hadis_tezi_inceleme_veya_ret():
    s = S.siniflandir(T("Buhârî'de iman bahsi hadislerinin tahlili", "Temel İslam Bilimleri Ana Bilim Dalı", "Hadis Bilim Dalı"))
    assert s.durum == "ret"


# ------------------------------------------------------------ İSNAD
def test_isnad():
    t = json.loads(fx("tezara_hit.json"))
    k = isnad.kaynakca(t)
    assert k.startswith("Pala, Ali İhsan. Fıkıh Usulü Açısından Beyan")
    assert k.endswith("Van: Yüzüncü Yıl Üniversitesi, Sosyal Bilimler Enstitüsü, Yüksek Lisans Tezi, 1995.")
    d = isnad.dipnot(t)
    assert d.startswith("Ali İhsan Pala, Fıkıh Usulü") and d.endswith("(Van: Yüzüncü Yıl Üniversitesi, Sosyal Bilimler Enstitüsü, Yüksek Lisans Tezi, 1995).")
    assert isnad.sehir("Necmettin Erbakan Üniversitesi") == "Konya"
    assert isnad.sehir("Ankara Yıldırım Beyazıt Üniversitesi") == "Ankara"
    assert isnad.sehir("Kütahya Dumlupınar Üniversitesi") == "Kütahya"


# ------------------------------------------------------------ uçtan uca (sahte sunucu)
def _ayar(tmp):
    a = ayarlari_yukle()
    a["veritabani"] = str(tmp / "t.db")
    a["cikti_klasoru"] = str(tmp / "cikti")
    return a


def test_tezara_uctan_uca(tmp_path):
    hit = json.loads(fx("tezara_hit.json"))
    alakasiz = dict(hit, id=50000, title_original="Beton dayanımı", department="İnşaat Mühendisliği Ana Bilim Dalı",
                    branch="", keywords=[], abstract_original="Beton", abstract_translated="")

    def handler(req: httpx.Request):
        body = json.loads(req.content)
        if req.url.path.endswith("facet-search"):
            v = {"department": [("Temel İslam Bilimleri Ana Bilim Dalı", 19000), ("İslam Ekonomisi ve Finansı Ana Bilim Dalı", 344)],
                 "branch": [("İslam Hukuku Bilim Dalı", 2256), ("Temel İşlemler ve Termodinamik Bilim Dalı", 264)]}[body["facetName"]]
            return httpx.Response(200, json={"facetHits": [{"value": a, "count": c} for a, c in v]})
        f = body.get("filter") or ""
        if "Termodinamik" in f:
            raise AssertionError("alakasız birim filtreye girmemeli")
        if body.get("hitsPerPage") == 1:
            return httpx.Response(200, json={"totalHits": 1, "hits": [{"id": 1}]})
        if f.startswith("id >"):
            return httpx.Response(200, json={"hits": [alakasiz], "totalPages": 1})
        if body.get("q"):
            return httpx.Response(200, json={"hits": [alakasiz], "totalPages": 1})
        return httpx.Response(200, json={"hits": [hit], "totalPages": 1})

    ist = TezaraIstemci("https://x", "k", istemci=httpx.Client(transport=httpx.MockTransport(handler)), uyku=lambda s: None)
    b = Boru(_ayar(tmp_path), S, Depo(tmp_path / "t.db"), tezara=ist)
    b.tezara_tara()
    b.tezara_guncelle()
    st = b.depo.istatistik()
    assert st["durum"].get("kabul") == 1
    assert not b.depo.var_mi(50000)  # alakasız tez saklanmadı
    sonuc = b.disa_aktar()
    assert sonuc["csv"] == 1 and sonuc["ris"] == 1
    site = json.loads((tmp_path / "cikti/site/tezler.json").read_text(encoding="utf-8"))
    assert site[0]["isnad"]["kaynakca_html"].startswith("Pala, Ali İhsan. <i>Fıkıh Usulü")
    ris = (tmp_path / "cikti/fikih_tezleri_zotero.ris").read_text(encoding="utf-8")
    assert "TY  - THES" in ris and "PB  - Yüzüncü Yıl Üniversitesi" in ris and "CY  - Van" in ris


def test_yok_uctan_uca(tmp_path):
    cagri = {"arama": 0}

    def handler(req: httpx.Request):
        p = req.url.path
        if p.endswith("tarama.jsp"):
            return httpx.Response(200, text=fx("yok_tarama.html"))
        if p.endswith("SearchTez"):
            cagri["arama"] += 1
            form = dict(httpx.QueryParams(req.content.decode()))
            assert form["islem"] == "2" and form["-find"] == "  Bul" and form["Durum"] == "0"
            if form.get("ABD") == "70" and form["yil1"] == "2024" and form["yil2"] == "2024":
                return httpx.Response(200, text=fx("yok_liste.html"))
            return httpx.Response(200, text='<div class="result-count-text"> kayıt bulunamadı </div>')
        if "tezBilgiDetay" in p:
            return httpx.Response(200, text=fx("yok_detay.json"))
        if "getTezPdf" in p:
            return httpx.Response(200, text=fx("yok_pdf.html"))
        return httpx.Response(404)

    c = httpx.Client(base_url="https://tez.yok.gov.tr/UlusalTezMerkezi/", transport=httpx.MockTransport(handler))
    o = YokOturum(0, 0, 0, 1, istemci=c, uyku=lambda s: None)
    a = _ayar(tmp_path)
    a["yok"]["en_eski_yil"] = 2024
    b = Boru(a, S, Depo(tmp_path / "t.db"), yok=o)
    b.sinif.ayar["anahtar_sorgular"] = []
    b.yok_tara(2024, 2024)
    t = {x["id"]: x for x in b.depo.tezler(["kabul"])}[1012137]
    assert t["id"] == 1012137 and t["branch"] == "İslam Hukuku Bilim Dalı"
    assert t["advisors"] == ["DOÇ. DR. MERVE ÖZAYKAL"] and t["pdf_url"]
    # ikinci satır: aynı sahte detay döndüğü için o da İslam Hukuku BD'de görünür; önemli olan tekrar çağrılmaması
    once = cagri["arama"]
    b.yok_tara(2024, 2024)  # tamamlanan sorgular atlanır
    assert cagri["arama"] == once


def test_yok_engel_durdurur(tmp_path):
    def handler(req):
        if req.url.path.endswith("tarama.jsp"):
            return httpx.Response(200, text=fx("yok_tarama.html"))
        return httpx.Response(200, text=fx("yok_engel.html"))
    c = httpx.Client(base_url="https://tez.yok.gov.tr/UlusalTezMerkezi/", transport=httpx.MockTransport(handler))
    o = YokOturum(0, 0, 0, 1, istemci=c, uyku=lambda s: None)
    o.ac()
    with pytest.raises(YokEngeli):
        o.ara(ABD="860")


def test_bolerek_ara_yil_boler():
    class Sahte:
        def __init__(self):
            self.sorgular = []

        def ara(self, **p):
            self.sorgular.append(p)
            y1, y2 = int(p["yil1"]), int(p["yil2"])
            n = 1500 * (y2 - y1 + 1)
            return (n, min(n, 2000), [])
    s = Sahte()
    parcalar = []
    bolerek_ara(s, {"ABD": "70"}, 2020, 2023, lambda p, r: parcalar.append((p["yil1"], p["yil2"])))
    assert parcalar == [(2020, 2020), (2021, 2021), (2022, 2022), (2023, 2023)]


# ------------------------------------------------------------ siteye aktarma
def test_siteye_aktar(tmp_path):
    from tezci import siteye_aktar as sa
    works = tmp_path / "src/content/works"
    works.mkdir(parents=True)
    (works / "pala-islam-2003.yaml").write_text(
        'type: tez-doktora\ntitle: "İslâm Hukuk Metodolojisinde Emir ve Nehyin Yorumu"\nauthors: ["Pala, Ali İhsan"]\n'
        'language: tr\nyear: 1995\nurl: "https://tez.yok.gov.tr/UlusalTezMerkezi/tezDetay.jsp?id=-E3S8tM8NEbYIQDl2EdFXw"\n'
        'addedAt: 2026-09-24\n', encoding="utf-8")
    t1 = json.loads(fx("tezara_hit.json"))
    t1["kategoriler"] = ["fikih", "fikih_usulu"]
    t2 = dict(t1, id=999001, detail_id_1="YENIKAYIT", title_original="Serahsî'nin istihsan anlayışı",
              author="AHMET YILMAZ", thesis_type="Doktora", pdf_url=None, advisors=["PROF. DR. HAYRETTİN KARAMAN"])
    kon = {"fikih_usulu": "Fıkıh usulü", "fukaha": "Şahıs çalışmaları"}
    r = sa.aktar([t1, t2], tmp_path, kon, bugun="2026-10-01")
    assert (r.yeni, r.tamamlanan, r.tur_duzeltilen) == (1, 1, 1)
    eski = (works / "pala-islam-2003.yaml").read_text(encoding="utf-8")
    assert "type: \"tez-yl\"" in eski and "yokId: 42575" in eski and 'year: 1995' in eski
    assert eski.index("yokId") < eski.index("addedAt")
    yeni = (works / "yilmaz-serahsi-istihsan-1995.yaml").read_text(encoding="utf-8")
    assert "origin: otomatik" in yeni and '"advisors": ' not in yeni
    assert 'advisors: ["Hayrettin Karaman"]' in yeni and 'topics: ["Fıkıh usulü"' in yeni
    # ikinci çalıştırma hiçbir şeyi değiştirmez
    r2 = sa.aktar([t1, t2], tmp_path, kon, bugun="2026-10-08")
    assert (r2.yeni, r2.tamamlanan, r2.degismeyen) == (0, 0, 2)
    # elle ret → yalnız otomatik kayıt silinir
    r3 = sa.aktar([], tmp_path, kon, cikarilacak={999001, 42575})
    assert r3.cikarilan == 1 and not (works / "yilmaz-serahsi-istihsan-1995.yaml").exists()
    assert (works / "pala-islam-2003.yaml").exists()
