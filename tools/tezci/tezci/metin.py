"""Türkçe metin yardımcıları: sadeleştirme, büyük/küçük harf, başlık düzeni, ad ayrıştırma."""
from __future__ import annotations

import html
import re
import unicodedata

_TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})
_TR_UPPER = str.maketrans({"i": "İ", "ı": "I"})
_FOLD = str.maketrans({
    "ı": "i", "ş": "s", "ç": "c", "ğ": "g", "ö": "o", "ü": "u",
    "â": "a", "î": "i", "û": "u", "ê": "e", "ô": "o",
    "’": "'", "‘": "'", "ʼ": "'", "ʻ": "'", "`": "'", "´": "'", "ʾ": "'", "ʿ": "'",
})


def lower_tr(s: str) -> str:
    return s.translate(_TR_LOWER).lower()


def upper_tr(s: str) -> str:
    return s.translate(_TR_UPPER).upper()


def fold(s: str | None) -> str:
    """Karşılaştırma için sadeleştirir: fıkhî → fikhi, ŞER'İYYE → ser'iyye."""
    if not s:
        return ""
    s = lower_tr(s).translate(_FOLD)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("'", "")  # şer'iyye = seriyye, Kur'an = Kuran
    return re.sub(r"\s+", " ", s).strip()


def clean_text(s: str | None) -> str:
    """HTML etiketlerini ve fazla boşlukları temizler."""
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = s.replace(" ", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    return s.strip()


def _cap_word(w: str) -> str:
    return upper_tr(w[:1]) + w[1:] if w else w


def title_case_tr(s: str | None) -> str:
    """Her kelimenin ilk harfini büyütür (Türkçe kurallarla). Ad/kurum adları için."""
    if not s:
        return ""
    s = lower_tr(s)
    return " ".join(_cap_word(w) for w in s.split(" "))


# İSNAD: bağlaç ve edatlar küçük yazılır (başta olmadıkça).
_SMALL_TR = {"ve", "ile", "veya", "ya", "yahut", "ki", "da", "de", "ta", "te",
             "mi", "mı", "mu", "mü", "ya da"}
_SMALL_EN = {"a", "an", "the", "and", "or", "nor", "but", "of", "in", "on", "at",
             "to", "for", "by", "with", "from", "as", "vs", "via"}
_ARTICLE = re.compile(r"^(el|er|es|ed|en|et|ez|ebu|ibn|b)(-)(.+)$", re.I)


def isnad_title(s: str | None) -> str:
    """Başlığı İSNAD başlık düzenine çevirir: Her Kelime Büyük, bağlaçlar küçük.

    "Ürdün Fetva Dairesi ve tıbbi fetvalarının mukayeseli analizi"
    → "Ürdün Fetva Dairesi ve Tıbbi Fetvalarının Mukayeseli Analizi"
    Tamamı büyük harfle girilmiş eski kayıtlar önce küçültülür.
    """
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s.strip())
    s = re.sub(r"(\w)([“«])", r"\1 \2", s)  # YÖK verisinde eksik boşluk: Beyan“İslam
    letters = [c for c in s if c.isalpha()]
    mostly_upper = letters and sum(c.isupper() for c in letters) / len(letters) > 0.7
    if mostly_upper:
        s = lower_tr(s)
    out = []
    after_colon = True
    for i, w in enumerate(s.split(" ")):
        bare = re.sub(r"[^\wçğıöşüâîû'-]", "", lower_tr(w))
        if not after_colon and (bare in _SMALL_TR or bare in _SMALL_EN):
            out.append(lower_tr(w) if not mostly_upper else w)
        else:
            m = _ARTICLE.match(w)
            if m and m.group(1).lower() in {"el", "er", "es", "ed", "en", "et", "ez"}:
                # Arapça harf-i tarif küçük kalır: el-Mebsût
                out.append(lower_tr(m.group(1)) + "-" + _cap_word(m.group(3)))
            elif w[:1] in "\"'“‘(«[":
                out.append(w[0] + _cap_word(w[1:]))
            else:
                out.append(_cap_word(w))
        after_colon = w.endswith((":", "?", "!", "."))
    return " ".join(out)


def split_name(full: str | None) -> tuple[str, str]:
    """'ALİ İHSAN PALA' → ('Pala', 'Ali İhsan'). Son kelime soyadı kabul edilir."""
    full = re.sub(r"\s+", " ", (full or "").strip())
    if not full:
        return "", ""
    full = title_case_tr(full)
    parts = full.split(" ")
    if len(parts) == 1:
        return parts[0], ""
    return parts[-1], " ".join(parts[:-1])


def thesis_type_label(t: str | None) -> str:
    f = fold(t)
    if "doktora" in f or "phd" in f:
        return "Doktora Tezi"
    if "yuksek lisans" in f or "master" in f:
        return "Yüksek Lisans Tezi"
    if "sanatta yeterlik" in f:
        return "Sanatta Yeterlik Tezi"
    if "tipta uzmanlik" in f:
        return "Tıpta Uzmanlık Tezi"
    return (t or "Tez").strip() + ("" if fold(t).endswith("tezi") else " Tezi")
