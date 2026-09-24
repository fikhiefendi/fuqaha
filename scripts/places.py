"""Place gazetteer for the jurists' map → src/data/places.yaml

Coordinates are approximate positions of the historical towns (for ruined or
renamed sites, the nearest modern town). Regions are the historical regions
used by the classical biographers, for filtering.
Run: python3 scripts/places.py
"""
import json
from pathlib import Path

REGIONS = {
    "hicaz": ("Hicaz", "Hijaz", "الحجاز"),
    "irak": ("Irak", "Iraq", "العراق"),
    "sam": ("Şam", "Syria", "الشام"),
    "cezire": ("Cezîre", "Jazira", "الجزيرة"),
    "misir": ("Mısır", "Egypt", "مصر"),
    "magrib": ("Mağrib", "Maghrib", "المغرب"),
    "endulus": ("Endülüs", "al-Andalus", "الأندلس"),
    "rum": ("Rum (Anadolu ve Rumeli)", "Rum (Anatolia and the Balkans)", "بلاد الروم"),
    "kirim": ("Kırım", "Crimea", "القرم"),
    "azerbaycan": ("Azerbaycan", "Azerbaijan", "أذربيجان"),
    "cibal": ("Cibâl", "Jibal", "الجبال"),
    "huzistan": ("Huzistan", "Khuzistan", "خوزستان"),
    "fars": ("Fars ve Kirman", "Fars and Kirman", "فارس وكرمان"),
    "taberistan": ("Taberistan ve Cürcan", "Tabaristan and Jurjan", "طبرستان وجرجان"),
    "horasan": ("Horasan", "Khurasan", "خراسان"),
    "sistan": ("Sistan", "Sistan", "سجستان"),
    "harezm": ("Harezm", "Khwarazm", "خوارزم"),
    "maveraunnehir": ("Mâverâünnehir", "Transoxiana", "ما وراء النهر"),
    "turkistan": ("Türkistan", "Turkestan", "تركستان"),
    "hind": ("Hind", "India", "الهند"),
    "habes": ("Habeşistan sahili", "Abyssinian coast", "ساحل الحبشة"),
}

# id: (tr, en, ar, region, lat, lng)
PLACES = {
    "medine": ("Medine", "Medina", "المدينة المنورة", "hicaz", 24.467, 39.611),
    "mekke": ("Mekke", "Mecca", "مكة المكرمة", "hicaz", 21.422, 39.826),
    "taif": ("Taif", "Ta'if", "الطائف", "hicaz", 21.270, 40.416),
    "kufe": ("Kûfe", "Kufa", "الكوفة", "irak", 32.030, 44.401),
    "basra": ("Basra", "Basra", "البصرة", "irak", 30.508, 47.783),
    "bagdat": ("Bağdat", "Baghdad", "بغداد", "irak", 33.315, 44.366),
    "vasit": ("Vâsıt", "Wasit", "واسط", "irak", 32.190, 46.300),
    "medain": ("Medâin", "al-Mada'in", "المدائن", "irak", 33.100, 44.580),
    "dimask": ("Dımaşk", "Damascus", "دمشق", "sam", 33.513, 36.292),
    "halep": ("Halep", "Aleppo", "حلب", "sam", 36.202, 37.158),
    "baalbek": ("Baalbek", "Baalbek", "بعلبك", "sam", 34.006, 36.204),
    "kudus": ("Kudüs", "Jerusalem", "القدس", "sam", 31.778, 35.235),
    "remle": ("Remle", "Ramla", "الرملة", "sam", 31.929, 34.872),
    "gazze": ("Gazze", "Gaza", "غزة", "sam", 31.502, 34.467),
    "tarsus": ("Tarsus", "Tarsus", "طرسوس", "sam", 36.918, 34.892),
    "ayintab": ("Ayıntab", "'Ayntab", "عينتاب", "sam", 37.066, 37.383),
    "mardin": ("Mardin", "Mardin", "ماردين", "cezire", 37.313, 40.735),
    "musul": ("Musul", "Mosul", "الموصل", "cezire", 36.340, 43.130),
    "rakka": ("Rakka", "Raqqa", "الرقة", "cezire", 35.950, 39.010),
    "suruc": ("Suruç", "Saruj", "سروج", "cezire", 36.976, 38.424),
    "fustat": ("Fustat", "Fustat", "الفسطاط", "misir", 30.006, 31.233),
    "kahire": ("Kahire", "Cairo", "القاهرة", "misir", 30.044, 31.262),
    "iskenderiye": ("İskenderiye", "Alexandria", "الإسكندرية", "misir", 31.200, 29.918),
    "taha": ("Taha", "Taha", "طحا", "misir", 28.100, 30.770),
    "meris": ("Merîs", "Maris", "مريس", "misir", 25.000, 32.600),
    "kayrevan": ("Kayrevan", "Kairouan", "القيروان", "magrib", 35.678, 10.096),
    "kurtuba": ("Kurtuba", "Córdoba", "قرطبة", "endulus", 37.888, -4.779),
    "istanbul": ("İstanbul", "Istanbul", "القسطنطينية", "rum", 41.008, 28.978),
    "edirne": ("Edirne", "Edirne", "أدرنة", "rum", 41.677, 26.556),
    "bursa": ("Bursa", "Bursa", "بروسة", "rum", 40.183, 29.061),
    "iznik": ("İznik", "Iznik", "إزنيق", "rum", 40.429, 29.721),
    "konya": ("Konya", "Konya", "قونية", "rum", 37.871, 32.485),
    "karaman": ("Karaman", "Karaman", "قرمان", "rum", 37.181, 33.215),
    "amasya": ("Amasya", "Amasya", "أماسية", "rum", 40.653, 35.833),
    "merzifon": ("Merzifon", "Merzifon", "مرزيفون", "rum", 40.873, 35.463),
    "ankara": ("Ankara", "Ankara", "أنقرة", "rum", 39.933, 32.859),
    "tokat": ("Tokat", "Tokat", "توقات", "rum", 40.314, 36.554),
    "samsun": ("Samsun", "Samsun", "سامسون", "rum", 41.287, 36.330),
    "sinop": ("Sinop", "Sinop", "سينوب", "rum", 42.026, 35.151),
    "kastamonu": ("Kastamonu", "Kastamonu", "قسطموني", "rum", 41.376, 33.776),
    "iskilip": ("İskilip", "Iskilip", "إسكليب", "rum", 40.735, 34.474),
    "sivrihisar": ("Sivrihisar", "Sivrihisar", "سفري حصار", "rum", 39.450, 31.537),
    "karahisar": ("Karahisar", "Karahisar", "قره حصار", "rum", 38.757, 30.538),
    "malatya": ("Malatya", "Malatya", "ملطية", "rum", 38.348, 38.312),
    "uskup": ("Üsküp", "Skopje", "أسكوب", "rum", 41.998, 21.425),
    "kirim": ("Kırım (Solhat)", "Crimea (Solkhat)", "القرم", "kirim", 45.057, 35.089),
    "berdaa": ("Berdea", "Barda'a", "بردعة", "azerbaycan", 40.374, 47.126),
    "tebriz": ("Tebriz", "Tabriz", "تبريز", "azerbaycan", 38.080, 46.292),
    "meraga": ("Merağa", "Maragha", "مراغة", "azerbaycan", 37.389, 46.237),
    "rey": ("Rey", "Rayy", "الري", "cibal", 35.588, 51.436),
    "isfahan": ("İsfahan", "Isfahan", "أصبهان", "cibal", 32.654, 51.668),
    "ramhurmuz": ("Râmhürmüz", "Ramhurmuz", "رامهرمز", "huzistan", 31.280, 49.604),
    "siraz": ("Şiraz", "Shiraz", "شيراز", "fars", 29.592, 52.584),
    "kirman": ("Kirman", "Kirman", "كرمان", "fars", 30.283, 57.079),
    "yezd": ("Yezd", "Yazd", "يزد", "fars", 31.897, 54.357),
    "taberistan": ("Taberistan (Âmül)", "Tabaristan (Amul)", "طبرستان", "taberistan", 36.470, 52.350),
    "curcan": ("Cürcan", "Jurjan", "جرجان", "taberistan", 37.250, 55.170),
    "esterabad": ("Esterabad", "Astarabad", "أستراباذ", "taberistan", 36.840, 54.430),
    "dihistan": ("Dihistan", "Dihistan", "دهستان", "taberistan", 37.600, 54.500),
    "nisabur": ("Nîşâbûr", "Nishapur", "نيسابور", "horasan", 36.213, 58.795),
    "merv": ("Merv", "Marw", "مرو", "horasan", 37.662, 62.193),
    "belh": ("Belh", "Balkh", "بلخ", "horasan", 36.758, 66.897),
    "herat": ("Herat", "Herat", "هراة", "horasan", 34.352, 62.204),
    "serahs": ("Serahs", "Sarakhs", "سرخس", "horasan", 36.544, 61.158),
    "beyhak": ("Beyhak", "Bayhaq", "بيهق", "horasan", 36.213, 57.682),
    "cam": ("Cam", "Jam", "جام", "horasan", 35.244, 60.623),
    "cuzcan": ("Cüzcan", "Juzjan", "جوزجان", "horasan", 36.667, 65.752),
    "velvalic": ("Velvalic", "Walwalij", "ولوالج", "horasan", 36.728, 68.857),
    "bistam": ("Bistam", "Bistam", "بسطام", "horasan", 36.485, 55.000),
    "damgan": ("Damgan", "Damghan", "دامغان", "horasan", 36.168, 54.342),
    "kumis": ("Kumis", "Qumis", "قومس", "horasan", 35.580, 53.390),
    "gazne": ("Gazne", "Ghazna", "غزنة", "hind", 33.549, 68.421),
    "lahor": ("Lahor", "Lahore", "لاهور", "hind", 31.549, 74.343),
    "sistan": ("Sistan", "Sistan", "سجستان", "sistan", 30.960, 61.860),
    "harezm": ("Harezm (Cürcaniyye)", "Khwarazm (Gurganj)", "خوارزم", "harezm", 42.330, 59.150),
    "buhara": ("Buhara", "Bukhara", "بخارى", "maveraunnehir", 39.775, 64.428),
    "semerkant": ("Semerkant", "Samarqand", "سمرقند", "maveraunnehir", 39.654, 66.975),
    "nesef": ("Nesef", "Nasaf", "نسف", "maveraunnehir", 38.860, 65.790),
    "kes": ("Keş", "Kish", "كش", "maveraunnehir", 39.060, 66.830),
    "kermine": ("Kermine", "Karmina", "كرمينية", "maveraunnehir", 40.140, 65.360),
    "tirmiz": ("Tirmiz", "Tirmidh", "ترمذ", "maveraunnehir", 37.224, 67.278),
    "sas": ("Şâş", "Shash", "الشاش", "maveraunnehir", 41.300, 69.240),
    "usrusene": ("Üsrûşene", "Usrushana", "أسروشنة", "maveraunnehir", 39.770, 68.820),
    "fergana": ("Fergana (Ahsiket)", "Farghana (Akhsikath)", "فرغانة", "maveraunnehir", 40.940, 71.430),
    "mergilan": ("Merginan", "Marghinan", "مرغينان", "maveraunnehir", 40.470, 71.720),
    "ozcend": ("Özcend", "Uzjand", "أوزجند", "maveraunnehir", 40.770, 73.300),
    "kasan": ("Kâsân", "Kasan", "كاسان", "maveraunnehir", 41.250, 71.550),
    "farab": ("Farab (Otrar)", "Farab (Otrar)", "فاراب", "turkistan", 42.850, 68.300),
    "isficab": ("İsficab", "Isbijab", "إسبيجاب", "turkistan", 42.300, 69.770),
    "signak": ("Siğnak", "Sighnaq", "سغناق", "turkistan", 44.140, 67.050),
    "kasgar": ("Kaşgar", "Kashghar", "كاشغر", "turkistan", 39.470, 75.990),
    "hit": ("Hît", "Hit", "هيت", "irak", 33.638, 42.826),
    "ukbera": ("Ukberâ", "'Ukbara", "عكبرا", "irak", 33.940, 44.180),
    "ahvaz": ("Ahvaz", "Ahwaz", "الأهواز", "huzistan", 31.318, 48.671),
    "ezriat": ("Ezriat (Der'a)", "Adhri'at (Dar'a)", "أذرعات", "sam", 32.625, 36.106),
    "hama": ("Hama", "Hama", "حماة", "sam", 35.132, 36.755),
    "hims": ("Humus", "Hims", "حمص", "sam", 34.731, 36.709),
    "hisnulekrad": ("Hısnü'l-Ekrad", "Hisn al-Akrad", "حصن الأكراد", "sam", 34.757, 36.294),
    "sencar": ("Sencar", "Sinjar", "سنجار", "cezire", 36.322, 41.876),
    "cuhfe": ("Cuhfe", "al-Juhfa", "الجحفة", "hicaz", 22.700, 39.140),
    "zeyla": ("Zeyla", "Zayla'", "زيلع", "habes", 11.353, 43.474),
    "kayseri": ("Kayseri", "Kayseri", "قيسارية", "rum", 38.722, 35.487),
    "kutahya": ("Kütahya", "Kütahya", "كوتاهية", "rum", 39.420, 29.983),
    "manisa": ("Manisa", "Manisa", "مغنيسا", "rum", 38.614, 27.429),
    "niksar": ("Niksar", "Niksar", "نكسار", "rum", 40.592, 36.952),
    "sivas": ("Sivas", "Sivas", "سيواس", "rum", 39.750, 37.015),
    "ahlat": ("Ahlat", "Akhlat", "خلاط", "rum", 38.753, 42.492),
    "hemedan": ("Hemedan", "Hamadhan", "همذان", "cibal", 34.799, 48.515),
    "siraf": ("Siraf", "Siraf", "سيراف", "fars", 27.665, 52.343),
    "tus": ("Tus", "Tus", "طوس", "horasan", 36.487, 59.518),
    "dehli": ("Delhi", "Delhi", "دهلي", "hind", 28.656, 77.231),
    "debusiye": ("Debusiye", "Dabusiyya", "دبوسية", "maveraunnehir", 39.720, 66.200),
    "beykend": ("Beykend", "Baykand", "بيكند", "maveraunnehir", 39.357, 63.939),
    "kesaniye": ("Keşaniye", "Kushaniyya", "كشانية", "maveraunnehir", 39.930, 66.630),
    "sugd": ("Suğd", "Sughd", "السغد", "maveraunnehir", 39.600, 67.400),
    "kus": ("Kus", "Qus", "قوص", "misir", 25.914, 32.763),
    "nigde": ("Niğde", "Nigde", "نكدة", "rum", 37.966, 34.679),
    "sarhad": ("Sarhad", "Salkhad", "صرخد", "sam", 32.492, 36.711),
    "taraz": ("Taraz", "Taraz", "طراز", "turkistan", 42.900, 71.370),
    "hucend": ("Hucend", "Khujand", "خجندة", "maveraunnehir", 40.283, 69.622),
}


def main():
    # Coordinates from the al-Thurayya gazetteer (CC BY 4.0) where a match exists;
    # see scripts/match_thurayya.py. Other places keep the approximate values above.
    matches_file = Path(__file__).parent.parent / "sources/thurayya-matches.json"
    matches = json.loads(matches_file.read_text()) if matches_file.exists() else {}
    out = ["# Generated by scripts/places.py — edit that file, not this one."]
    for pid, (tr, en, ar, region, lat, lng) in PLACES.items():
        m = matches.get(pid)
        if m:
            lat, lng = m["lat"], m["lng"]
        rtr, ren, rar = REGIONS[region]
        q = lambda v: json.dumps(v, ensure_ascii=False)
        out.append(
            f"{pid}:\n  name: {{ tr: {q(tr)}, en: {q(en)}, ar: {q(ar)} }}\n"
            f"  region: {{ tr: {q(rtr)}, en: {q(ren)}, ar: {q(rar)} }}\n  regionId: {region}\n"
            f"  lat: {lat}\n  lng: {lng}"
            + (f"\n  uri: {m['uri']}\n  coordSource: thurayya" if m else "\n  coordSource: approx")
        )
    path = Path(__file__).parent.parent / "src/data/places.yaml"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(len(PLACES), "places →", path)


if __name__ == "__main__":
    main()
