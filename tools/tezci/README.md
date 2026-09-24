# Tez toplayıcı (tezci)

YÖK Ulusal Tez Merkezi'ndeki **Fıkıh ve İslâm Hukuku, Fıkıh Usûlü, Fıkıh Tarihi,
Fukahânın Görüşleri ve Eserleri, Mukayeseli İslâm Hukuku, İslâm İktisadı** tezlerini
toplar, ilgisiz olanları ayıklar ve Fuqaha kaynakçasına (`src/content/works/`) ekler.

GitHub Actions'ta haftada iki kez kendiliğinden çalışır (`.github/workflows/tez-guncelle.yml`):
yeni tez varsa commit atar ve siteyi yeniden yayınlar. Elle çalıştırmak için:
**Actions → Tez güncelleme → Run workflow**.

## Akış

```
tezara.org (YÖK verisinin temizlenmiş kopyası)  ─┐
YÖK (tez.yok.gov.tr, doğrudan; yerelde isteğe bağlı) ─┴─► sınıflandırıcı ─► veri/tezler.db ─► src/content/works/*.yaml
                                                       (config/alanlar.yaml)
```

1. **Toplama.** İlk çalıştırmada ilgili tüm ABD/bilim dallarının tezleri ve anahtar sorgu
   sonuçları çekilir. Sonraki çalıştırmalarda yalnızca yeni Tez No'lar; ayda bir de
   birimlerin tamamı geç eklenen eski tezler için kontrol edilir.
2. **Ayıklama** (`config/alanlar.yaml`, kod bilmeden düzenlenebilir):
   - *Çekirdek birimler* (İslâm Hukuku ABD/BD, Fıkıh, İslâm İktisadı/Ekonomisi, Katılım
     Bankacılığı…) → doğrudan kabul.
   - *Geniş birimler* (Temel İslâm Bilimleri, İlahiyat, İslâm Tarihi, Din Bilimleri…) →
     her tez puanlanır. Tefsir, Hadis, Kelâm gibi dallarda eşik daha yüksektir.
   - *Diğer bölümler* (Hukuk, Tarih, İktisat, İşletme…) → yalnızca güçlü bir sinyal
     (fıkıh, İslâm hukuku, fetva, katılım bankacılığı…) varsa otomatik kabul; “faiz, miras,
     vakıf, kadı, nikâh, şer'iyye sicili” gibi bağlama bağlı terimler en fazla incelemeye düşer.
   - Puan: başlık ×3, anahtar kelime ×2, özet ×1. ≥6 kabul, 3–5 inceleme, <3 ret.
3. **Siteye aktarma** (`python -m tezci siteye-aktar`):
   - Sitede zaten olan bir tez yeniden yazılmaz, yalnızca eksik alanları eklenir.
     Eşleşme: `yokId` → YÖK bağlantısı → yazar soyadı + başlık benzerliği.
   - Yeni tezler `origin: otomatik` ile yazılır. Bu kayıtların yalnızca Türkçe ayrıntı
     sayfası üretilir, İngilizce/Arapça adresleri Türkçeye yönlenir (GitHub Pages'in 1 GB
     sınırının altında kalmak için).
   - Kategoriler sitedeki **Konu** etiketine dönüşür: Fıkıh usulü, Fıkıh tarihi, Şahıs
     çalışmaları, Mukayeseli hukuk, İslam iktisadı; başlıkta mezhep geçiyorsa Hanefîlik,
     Şâfiîlik vb. (eşleme: `config/ayarlar.yaml → site.konu_eslemesi`).
   - Her karar `sources/tezci-rapor.txt` dosyasına yazılır.

## Elle karar (inceleme)

Her çalıştırma, sistemin emin olamadığı tezleri `sources/incelenecek-tezler.csv` dosyasına yazar.

1. O dosyayı indirip **Karar** sütununa `kabul` veya `ret` yazın.
2. Dosyayı `tools/tezci/kararlar.csv` adıyla depoya yükleyin (GitHub'da *Add file → Upload files*).
3. Sonraki çalıştırmada kararlar uygulanır: `kabul` edilenler siteye eklenir, otomatik
   eklenmiş bir tez için verilen `ret` kararı o kaydı siteden çıkarır. Kararlar kalıcıdır.

Siteye girmiş ama yanlış bulduğunuz bir tezi çıkarmak için de aynı dosyaya
`Tez No` ve `ret` yazmanız yeterli (Tez No kayıt dosyasındaki `yokId` değeridir).

## Alan tanımını değiştirme

`config/alanlar.yaml` dosyasına terim, fakih adı veya birim ekleyip commit atın. Sonraki
çalıştırma dosyanın değiştiğini fark eder ve kayıtlı bütün tezleri (reddedilenler dahil)
yeniden sınıflandırır; yeni kabul edilenler siteye eklenir. Yeniden indirme gerekmez.
Sınıflandırma sonucu değişip artık kabul edilmeyen, önceden otomatik eklenmiş kayıtlar
siteden kendiliğinden silinmez; bunlar için `kararlar.csv` ile `ret` kararı verin.

## Yerelde çalıştırma

```bash
cd tools/tezci
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m tezci tara --kaynak tezara     # ilk tarama (dakikalar)
python -m tezci siteye-aktar             # src/content/works'e yaz
python -m tezci disa-aktar               # cikti/: İSNAD sütunlu CSV, Zotero RIS, JSON
python -m tezci durum                    # sayılar
python -m pytest -q tests                # testler
```

YÖK'ten doğrudan çekmek için `--kaynak yok` (yavaştır: YÖK kısa sürede çok arama yapan
bağlantıya geçici “TR7” engel sayfası döndürdüğü için aramalar arası 30 sn beklenir;
kesilirse aynı komutla kaldığı yerden devam eder). GitHub Actions'ta YÖK kullanılmaz,
çünkü YÖK yurt dışı IP'leri engelleyebilir.

## Dosyalar

| Dosya | İşlev |
|---|---|
| `tezci/kaynak_tezara.py` | tezara.org arama altyapısı (Meilisearch) istemcisi |
| `tezci/kaynak_yok.py` | YÖK istemcisi: oturum, form, 2000 sınırını aşmak için bölerek arama, detay, PDF, engel algılama |
| `tezci/siniflandir.py` | Puanlama ve kategoriler |
| `tezci/siteye_aktar.py` | Kaynakça YAML'larına yazma, eşleştirme |
| `tezci/isnad.py`, `tezci/disa_aktar.py` | İSNAD künyeleri; CSV/RIS/JSON çıktıları |
| `tezci/db.py`, `tezci/boru.py`, `tezci/cli.py` | Veritabanı, akış, komutlar |
| `config/alanlar.yaml` | Neyin ilgili sayılacağı |
| `config/ayarlar.yaml` | Kaynak, bekleme süreleri, site ayarları |

Teşekkür: YÖK form ayrıntıları ve tezara.org arama altyapısı, tezara'nın MIT lisanslı
açık kaynak kodundan (github.com/yekta/tezara) öğrenilmiştir.
