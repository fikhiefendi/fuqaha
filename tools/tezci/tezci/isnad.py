"""İSNAD Atıf Sistemi (2. edisyon) — tez künyeleri.

Kaynakça:  Soyadı, Adı. Tezin Adı. Şehir: Üniversite, Enstitü, Tez Türü, Yıl.
Dipnot  :  Adı Soyadı, Tezin Adı (Şehir: Üniversite, Enstitü, Tez Türü, Yıl), s.
Tez adı italik yazılır (HTML çıktısında <i>), başlık düzeninde (her kelime büyük,
bağlaçlar küçük). Şehir, üniversite adından çıkarılır; bulunamazsa atlanır.
"""
from __future__ import annotations

from .metin import fold, isnad_title, split_name, thesis_type_label, title_case_tr

ILLER = """Adana Adıyaman Afyonkarahisar Ağrı Aksaray Amasya Ankara Antalya Ardahan Artvin Aydın
Balıkesir Bartın Batman Bayburt Bilecik Bingöl Bitlis Bolu Burdur Bursa Çanakkale Çankırı Çorum
Denizli Diyarbakır Düzce Edirne Elazığ Erzincan Erzurum Eskişehir Gaziantep Giresun Gümüşhane
Hakkari Hatay Iğdır Isparta İstanbul İzmir Kahramanmaraş Karabük Karaman Kars Kastamonu Kayseri
Kırıkkale Kırklareli Kırşehir Kilis Kocaeli Konya Kütahya Malatya Manisa Mardin Mersin Muğla Muş
Nevşehir Niğde Ordu Osmaniye Rize Sakarya Samsun Siirt Sinop Sivas Şanlıurfa Şırnak Tekirdağ Tokat
Trabzon Tunceli Uşak Van Yalova Yozgat Zonguldak""".split()

# Adında il geçmeyen üniversiteler (sadeleştirilmiş ad parçası → il)
OZEL = {
    "marmara": "İstanbul", "bogazici": "İstanbul", "galatasaray": "İstanbul", "yeditepe": "İstanbul",
    "ibn haldun": "İstanbul", "sabahattin zaim": "İstanbul", "fatih sultan mehmet": "İstanbul",
    "29 mayis": "İstanbul", "medeniyet": "İstanbul", "yildiz teknik": "İstanbul", "bahcesehir": "İstanbul",
    "mimar sinan": "İstanbul", "fatih universitesi": "İstanbul", "kadir has": "İstanbul", "sehir universitesi": "İstanbul",
    "ege universitesi": "İzmir", "dokuz eylul": "İzmir", "katip celebi": "İzmir",
    "uludag": "Bursa", "selcuk": "Konya", "necmettin erbakan": "Konya", "karatay": "Konya",
    "ataturk universitesi": "Erzurum", "ondokuz mayis": "Samsun", "yuzuncu yil": "Van",
    "cumhuriyet": "Sivas", "firat": "Elazığ", "dicle": "Diyarbakır", "harran": "Şanlıurfa",
    "inonu": "Malatya", "erciyes": "Kayseri", "cukurova": "Adana", "akdeniz": "Antalya",
    "karadeniz teknik": "Trabzon", "kafkas": "Kars", "hitit": "Çorum", "bozok": "Yozgat",
    "dumlupinar": "Kütahya", "pamukkale": "Denizli", "suleyman demirel": "Isparta",
    "mehmet akif ersoy": "Burdur", "sutcu imam": "Kahramanmaraş", "mustafa kemal": "Hatay",
    "onsekiz mart": "Çanakkale", "trakya": "Edirne", "namik kemal": "Tekirdağ", "celal bayar": "Manisa",
    "kocatepe": "Afyonkarahisar", "osmangazi": "Eskişehir", "anadolu universitesi": "Eskişehir",
    "gazi universitesi": "Ankara", "hacettepe": "Ankara", "bilkent": "Ankara", "orta dogu teknik": "Ankara",
    "baskent": "Ankara", "haci bayram": "Ankara", "abant izzet baysal": "Bolu",
    "haci bektas veli": "Nevşehir", "omer halisdemir": "Niğde", "karamanoglu mehmetbey": "Karaman",
    "ahi evran": "Kırşehir", "karatekin": "Çankırı", "bulent ecevit": "Zonguldak",
    "recep tayyip erdogan": "Rize", "alparslan": "Muş", "ibrahim cecen": "Ağrı", "artuklu": "Mardin",
    "bitlis eren": "Bitlis", "adnan menderes": "Aydın", "sitki kocman": "Muğla",
    "gaziosmanpasa": "Tokat", "kirikkale": "Kırıkkale", "seyh edebali": "Bilecik",
}
_ILLER_F = [(fold(i), i) for i in ILLER]


def sehir(universite: str | None) -> str:
    f = fold(universite)
    if not f:
        return ""
    for parca, il in OZEL.items():
        if parca in f:
            return il
    en_iyi = None
    for fi, il in _ILLER_F:
        i = f.find(fi)
        if i >= 0 and (i == 0 or not f[i - 1].isalnum()) and (en_iyi is None or i < en_iyi[0]):
            en_iyi = (i, il)
    return en_iyi[1] if en_iyi else ""


def _yayin_bilgisi(t: dict) -> str:
    uni = (t.get("university") or "").strip()
    ens = (t.get("institute") or "").strip()
    tur = thesis_type_label(t.get("thesis_type"))
    yil = str(t.get("year") or "t.y.")
    sh = sehir(uni)
    govde = ", ".join(x for x in [uni, ens, tur, yil] if x)
    return f"{sh}: {govde}" if sh else govde


def _adlar(t: dict) -> tuple[str, str]:
    soyad, ad = split_name(t.get("author"))
    return soyad, ad


def kaynakca(t: dict, html: bool = False) -> str:
    soyad, ad = _adlar(t)
    yazar = f"{soyad}, {ad}" if ad else soyad
    baslik = isnad_title(t.get("title_original"))
    baslik = f"<i>{baslik}</i>" if html else baslik
    return f"{yazar}. {baslik}. {_yayin_bilgisi(t)}."


def dipnot(t: dict, html: bool = False) -> str:
    soyad, ad = _adlar(t)
    yazar = f"{ad} {soyad}".strip()
    baslik = isnad_title(t.get("title_original"))
    baslik = f"<i>{baslik}</i>" if html else baslik
    return f"{yazar}, {baslik} ({_yayin_bilgisi(t)})."


def kisa_dipnot(t: dict) -> str:
    """Sonraki atıflar: Soyadı, Kısa Başlık, s."""
    soyad, _ = _adlar(t)
    kelimeler = isnad_title(t.get("title_original")).split()
    return f"{soyad}, {' '.join(kelimeler[:4])}"


__all__ = ["kaynakca", "dipnot", "kisa_dipnot", "sehir", "title_case_tr"]
