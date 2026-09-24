// Site-wide settings.
export const SITE = {
  name: 'Fuqaha',
  nameAr: 'فقهاء',
};

export const MADHHABS = {
  hanefi: { tr: 'Hanefî', en: 'Ḥanafī', ar: 'الحنفي', color: '#2d5446' },
  maliki: { tr: 'Mâlikî', en: 'Mālikī', ar: 'المالكي', color: '#9a5b2e' },
  safii: { tr: 'Şâfiî', en: 'Shāfiʿī', ar: 'الشافعي', color: '#34507f' },
  hanbeli: { tr: 'Hanbelî', en: 'Ḥanbalī', ar: 'الحنبلي', color: '#7a3e62' },
  zahiri: { tr: 'Zâhirî', en: 'Ẓāhirī', ar: 'الظاهري', color: '#6b6b2f' },
  diger: { tr: 'Diğer', en: 'Other', ar: 'غير ذلك', color: '#6f6a60' },
} as const;

export const WORK_TYPES = {
  kitap: { tr: 'Kitap', en: 'Book', ar: 'كتاب' },
  makale: { tr: 'Makale', en: 'Article', ar: 'بحث' },
  'tez-doktora': { tr: 'Doktora tezi', en: 'PhD thesis', ar: 'أطروحة دكتوراه' },
  'tez-yl': { tr: 'Yüksek lisans tezi', en: 'MA thesis', ar: 'رسالة ماجستير' },
  tahkik: { tr: 'Tahkik', en: 'Critical edition', ar: 'تحقيق' },
  ceviri: { tr: 'Çeviri', en: 'Translation', ar: 'ترجمة' },
  bildiri: { tr: 'Bildiri', en: 'Conference paper', ar: 'ورقة مؤتمر' },
  ansiklopedi: { tr: 'Ansiklopedi maddesi', en: 'Encyclopaedia entry', ar: 'مادة موسوعية' },
} as const;
