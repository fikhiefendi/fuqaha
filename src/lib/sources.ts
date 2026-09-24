import type { Lang } from '../i18n/ui';

// Bibliographic forms of the printed works the biographies are taken from,
// so that readers cite the source itself rather than this website.
type Forms = {
  /** Style name shown above each reference. */
  styles: [string, string, string];
  note: (page: string) => string;
  short: (page: string) => string;
  bib: string;
};

const FAWAID: Record<Lang, Forms> = {
  tr: {
    styles: ['ISNAD · ilk dipnot', 'ISNAD · sonraki dipnotlar', 'ISNAD · kaynakça'],
    note: (p) =>
      `Ebü’l-Hasenât Muhammed Abdülhay el-Leknevî, el-Fevâidü’l-behiyye fî terâcimi’l-Hanefiyye, nşr. Muhammed Bedrüddin Ebû Firâs en-Na‘sânî (Mısır: Matbaatü Dâri’s-saâde, 1324), ${p}.`,
    short: (p) => `Leknevî, el-Fevâidü’l-behiyye, ${p}.`,
    bib: 'Leknevî, Ebü’l-Hasenât Muhammed Abdülhay. el-Fevâidü’l-behiyye fî terâcimi’l-Hanefiyye. nşr. Muhammed Bedrüddin Ebû Firâs en-Na‘sânî. Mısır: Matbaatü Dâri’s-saâde, 1324.',
  },
  en: {
    styles: ['Chicago · first note', 'Chicago · short note', 'Chicago · bibliography'],
    note: (p) =>
      `Abū al-Ḥasanāt Muḥammad ʿAbd al-Ḥayy al-Laknawī, al-Fawāʾid al-bahiyya fī tarājim al-Ḥanafiyya, ed. Muḥammad Badr al-Dīn Abū Firās al-Naʿsānī (Cairo: Maṭbaʿat Dār al-Saʿāda, 1324/1906), ${p}.`,
    short: (p) => `Laknawī, al-Fawāʾid al-bahiyya, ${p}.`,
    bib: 'Laknawī, Abū al-Ḥasanāt Muḥammad ʿAbd al-Ḥayy al-. al-Fawāʾid al-bahiyya fī tarājim al-Ḥanafiyya. Edited by Muḥammad Badr al-Dīn Abū Firās al-Naʿsānī. Cairo: Maṭbaʿat Dār al-Saʿāda, 1324/1906.',
  },
  ar: {
    styles: ['الحاشية', 'الحاشية المختصرة', 'قائمة المصادر'],
    note: (p) => `أبو الحسنات محمد عبد الحي اللكنوي، الفوائد البهية في تراجم الحنفية، عني بتصحيحه محمد بدر الدين أبو فراس النعساني (مصر: مطبعة دار السعادة، ١٣٢٤هـ)، ص ${p}.`,
    short: (p) => `اللكنوي، الفوائد البهية، ص ${p}.`,
    bib: 'اللكنوي، أبو الحسنات محمد عبد الحي. الفوائد البهية في تراجم الحنفية. عني بتصحيحه محمد بدر الدين أبو فراس النعساني. مصر: مطبعة دار السعادة، ١٣٢٤هـ.',
  },
};

const BOOKS: Record<string, Record<Lang, Forms>> = {
  'الفوائد البهية في تراجم الحنفية': FAWAID,
};

export function sourceForms(book: string, lang: Lang): Forms | undefined {
  return BOOKS[book]?.[lang];
}
