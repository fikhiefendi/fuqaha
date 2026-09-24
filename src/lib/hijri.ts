// Hijri → Gregorian conversion with the tabular (arithmetical) Islamic calendar.
// Dates before 15 October 1582 are given in the Julian calendar, as historians do.
// The tabular calendar can differ from the observed month start by a day or two,
// so exact days are indicative; years are reliable.

const ISLAMIC_EPOCH = 1948439.5; // JD of 1 Muharram 1 AH (civil epoch)

function hijriToJd(year: number, month = 1, day = 1): number {
  return (
    day +
    Math.ceil(29.5 * (month - 1)) +
    (year - 1) * 354 +
    Math.floor((3 + 11 * year) / 30) +
    ISLAMIC_EPOCH -
    1
  );
}

/** JD → { year, month, day } in the Julian (before 1582-10-15) or Gregorian calendar. */
function jdToCivil(jd: number) {
  const z = Math.floor(jd + 0.5);
  let a = z;
  if (z >= 2299161) {
    const alpha = Math.floor((z - 1867216.25) / 36524.25);
    a = z + 1 + alpha - Math.floor(alpha / 4);
  }
  const b = a + 1524;
  const c = Math.floor((b - 122.1) / 365.25);
  const d = Math.floor(365.25 * c);
  const e = Math.floor((b - d) / 30.6001);
  const day = b - d - Math.floor(30.6001 * e);
  const month = e < 14 ? e - 1 : e - 13;
  const year = month > 2 ? c - 4716 : c - 4715;
  return { year, month, day };
}

function yearsSpanned(start: number, end: number) {
  const a = jdToCivil(start).year;
  const b = jdToCivil(end).year;
  if (a === b) return `${a}`;
  // 1139-40 style when both years share the same century
  return Math.floor(a / 100) === Math.floor(b / 100) ? `${a}-${String(b).slice(-2)}` : `${a}-${b}`;
}

/** Gregorian (or Julian) equivalent: a year range for a year, a month's span, or an exact date. */
export function miladi(year: number, month?: number, day?: number): string {
  if (month && day) return `${jdToCivil(hijriToJd(year, month, day)).year}`;
  if (month) {
    const start = hijriToJd(year, month, 1);
    const end = month === 12 ? hijriToJd(year + 1, 1, 1) - 1 : hijriToJd(year, month + 1, 1) - 1;
    return yearsSpanned(start, end);
  }
  return yearsSpanned(hijriToJd(year, 1, 1), hijriToJd(year + 1, 1, 1) - 1);
}

/** "534/1139-40" */
export function hm(year: number, month?: number, day?: number): string {
  return `${year}/${miladi(year, month, day)}`;
}

export const HIJRI_MONTHS = {
  tr: ['Muharrem', 'Safer', 'Rebîülevvel', 'Rebîülâhir', 'Cemâziyelevvel', 'Cemâziyelâhir', 'Receb', 'Şaban', 'Ramazan', 'Şevval', 'Zilkade', 'Zilhicce'],
  en: ['Muharram', 'Safar', 'Rabi I', 'Rabi II', 'Jumada I', 'Jumada II', 'Rajab', "Sha'ban", 'Ramadan', 'Shawwal', "Dhu al-Qa'da", 'Dhu al-Hijja'],
  ar: ['المحرم', 'صفر', 'ربيع الأول', 'ربيع الآخر', 'جمادى الأولى', 'جمادى الآخرة', 'رجب', 'شعبان', 'رمضان', 'شوال', 'ذو القعدة', 'ذو الحجة'],
} as const;

/** Full reading for detail pages, e.g. "26 Rebîülevvel 534/1139". */
export function hmLong(lang: 'tr' | 'en' | 'ar', year: number, month?: number, day?: number): string {
  const m = month ? HIJRI_MONTHS[lang][month - 1] : '';
  const parts = [day, m].filter(Boolean).join(' ');
  return `${parts ? parts + ' ' : ''}${hm(year, month, day)}`;
}
