import type { ImageMetadata } from 'astro';
import type { Lang, Localized } from '../i18n/ui';
import credits from '../data/image-credits.json';
import library from '../assets/images/library.jpg';
import ulughbeg from '../assets/images/ulughbeg.jpg';
import registan from '../assets/images/registan.jpg';
import mustansiriya from '../assets/images/mustansiriya.jpg';
import bouinania from '../assets/images/bouinania.jpg';
import bayezid from '../assets/images/bayezid.jpg';
import idrisi from '../assets/images/idrisi.jpg';
import istakhri from '../assets/images/istakhri.jpg';
import mabsut from '../assets/images/mabsut.jpg';
import kharaj from '../assets/images/kharaj.jpg';
import multaqa from '../assets/images/multaqa.jpg';

export type PhotoId = keyof typeof credits;
export type Photo = {
  id: PhotoId;
  src: ImageMetadata;
  caption: Required<Localized>;
  credit: { title: string; page: string; artist: string; license: string; licenseUrl?: string };
};

const SRC: Record<PhotoId, ImageMetadata> = {
  library, ulughbeg, registan, mustansiriya, bouinania, bayezid, idrisi, istakhri, mabsut, kharaj, multaqa,
};

const CAPTIONS: Record<PhotoId, Required<Localized>> = {
  library: {
    tr: 'Kütüphanede bir ilim meclisi. Vâsıtî’nin Harîrî’nin Makāmât’ı için yaptığı tasvir, Bağdat, 634/1237',
    en: 'A gathering of scholars in a library. Al-Wāsiṭī’s illustration to al-Ḥarīrī’s Maqāmāt, Baghdad, 634/1237',
    ar: 'مجلس علم في مكتبة، من تصاوير الواسطي لمقامات الحريري، بغداد، ٦٣٤هـ',
  },
  ulughbeg: {
    tr: 'Uluğ Bey Medresesi, Semerkant, 823/1420',
    en: 'The Ulugh Beg Madrasa, Samarkand, 823/1420',
    ar: 'مدرسة ألغ بيك، سمرقند، ٨٢٣هـ',
  },
  registan: {
    tr: 'Registan Meydanı ve medreseleri, Semerkant',
    en: 'The Registan and its madrasas, Samarkand',
    ar: 'ساحة ريكستان ومدارسها، سمرقند',
  },
  mustansiriya: {
    tr: 'Müstansıriye Medresesi, Bağdat, 631/1234',
    en: 'The Mustanṣiriyya Madrasa, Baghdad, 631/1234',
    ar: 'المدرسة المستنصرية، بغداد، ٦٣١هـ',
  },
  bouinania: {
    tr: 'Bû İnâniyye Medresesi’nin avlusu, Fas, 756/1355',
    en: 'Courtyard of the Bū ʿInāniyya Madrasa, Fez, 756/1355',
    ar: 'صحن المدرسة البوعنانية، فاس، ٧٥٦هـ',
  },
  bayezid: {
    tr: 'Yıldırım Bayezid Medresesi, Bursa',
    en: 'The Yıldırım Bayezid Madrasa, Bursa',
    ar: 'مدرسة يلدرم بايزيد، بورصة',
  },
  idrisi: {
    tr: 'İdrîsî’nin dünya haritası (548/1154), Konrad Miller’in 1929 tarihli kopyası',
    en: 'Al-Idrīsī’s world map (548/1154), Konrad Miller’s copy of 1929',
    ar: 'خريطة العالم للإدريسي (٥٤٨هـ)، نسخة كونراد ميلر سنة ١٩٢٩م',
  },
  istakhri: {
    tr: 'Fars Denizi. İstahrî’nin Mesâlikü’l-memâlik’inin bir nüshasından',
    en: 'The Persian Sea, from a copy of al-Iṣṭakhrī’s Masālik al-mamālik',
    ar: 'بحر فارس، من نسخة من مسالك الممالك للإصطخري',
  },
  mabsut: {
    tr: 'Serahsî, el-Mebsût. 622/1225 tarihli nüsha',
    en: 'Al-Sarakhsī, al-Mabsūṭ. Copy dated 622/1225',
    ar: 'المبسوط للسرخسي، نسخة مؤرخة ٦٢٢هـ',
  },
  kharaj: {
    tr: 'Ebû Yûsuf, Kitâbü’l-Harâc. 961/1554 tarihli nüsha',
    en: 'Abū Yūsuf, Kitāb al-Kharāj. Copy dated 961/1554',
    ar: 'كتاب الخراج لأبي يوسف، نسخة مؤرخة ٩٦١هـ',
  },
  multaqa: {
    tr: 'İbrâhim el-Halebî, Mülteka’l-ebhur. 11./17. yüzyıl nüshası',
    en: 'Ibrāhīm al-Ḥalabī, Multaqā al-abḥur. 11th/17th-century copy',
    ar: 'ملتقى الأبحر لإبراهيم الحلبي، نسخة من القرن الحادي عشر',
  },
};

export const PHOTOS: Photo[] = (Object.keys(SRC) as PhotoId[]).map((id) => ({
  id,
  src: SRC[id],
  caption: CAPTIONS[id],
  credit: credits[id],
}));

export const photo = (id: PhotoId) => PHOTOS.find((p) => p.id === id)!;

/** Architecture photos used behind slides that have no image of their own. */
const BACKDROPS: PhotoId[] = ['ulughbeg', 'mustansiriya', 'registan', 'bouinania', 'bayezid'];
export function backdrop(seed: string) {
  let h = 0;
  for (const c of seed) h = (h * 31 + c.codePointAt(0)!) >>> 0;
  return photo(BACKDROPS[h % BACKDROPS.length]);
}

/** "Public domain" is shown in the reader's language; licence names stay as they are. */
export function licenseLabel(p: Photo, lang: Lang) {
  if (p.credit.license !== 'Public domain') return p.credit.license;
  return { tr: 'Kamu malı', en: 'Public domain', ar: 'ملك عام' }[lang];
}
