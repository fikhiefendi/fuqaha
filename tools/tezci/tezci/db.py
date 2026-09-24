"""SQLite depolama. Tüm çekilen tezler (reddedilenler dahil) saklanır; böylece
alan tanımları değiştiğinde yeniden indirmeden yeniden sınıflandırma yapılabilir."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

SEMA = """
CREATE TABLE IF NOT EXISTS tezler (
    id                  INTEGER PRIMARY KEY,      -- YÖK Tez No
    title_original      TEXT,
    title_translated    TEXT,
    author              TEXT,
    advisors            TEXT,   -- JSON liste
    university          TEXT,
    institute           TEXT,
    department          TEXT,
    branch              TEXT,
    year                INTEGER,
    thesis_type         TEXT,
    language            TEXT,
    subjects            TEXT,   -- JSON
    keywords            TEXT,   -- JSON
    abstract_original   TEXT,
    abstract_translated TEXT,
    pdf_url             TEXT,
    restricted          INTEGER,
    detail_id_1         TEXT,
    detail_id_2         TEXT,
    kaynak              TEXT,   -- 'yok' | 'tezara'
    ilk_gorulme         TEXT,
    son_guncelleme      TEXT,
    -- sınıflandırma
    durum               TEXT,   -- kabul | inceleme | ret
    puan                INTEGER,
    kategoriler         TEXT,   -- JSON
    gerekce             TEXT,   -- JSON
    manuel              INTEGER DEFAULT 0,  -- 1: elle karar verildi, otomatik değiştirilmez
    siniflandirma_surum INTEGER
);
CREATE INDEX IF NOT EXISTS ix_tez_durum ON tezler(durum);
CREATE INDEX IF NOT EXISTS ix_tez_yil ON tezler(year);

CREATE TABLE IF NOT EXISTS sorgular (       -- devam ettirilebilir tarama için
    anahtar     TEXT PRIMARY KEY,
    kaynak      TEXT,
    parametre   TEXT,
    bulunan     INTEGER,
    durum       TEXT,        -- tamam | hata
    zaman       TEXT
);

CREATE TABLE IF NOT EXISTS calismalar (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    baslangic   TEXT,
    bitis       TEXT,
    komut       TEXT,
    yeni        INTEGER DEFAULT 0,
    guncellenen INTEGER DEFAULT 0,
    kabul       INTEGER DEFAULT 0,
    notlar      TEXT
);

CREATE TABLE IF NOT EXISTS durum_bilgisi (
    anahtar TEXT PRIMARY KEY,
    deger   TEXT
);
"""

ALANLAR = [
    "id", "title_original", "title_translated", "author", "advisors", "university", "institute",
    "department", "branch", "year", "thesis_type", "language", "subjects", "keywords",
    "abstract_original", "abstract_translated", "pdf_url", "restricted", "detail_id_1", "detail_id_2",
]
JSON_ALANLAR = {"advisors", "subjects", "keywords", "kategoriler", "gerekce"}


def simdi() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Depo:
    def __init__(self, yol: str | Path):
        Path(yol).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(yol))
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.executescript(SEMA)

    def close(self):
        self.con.commit()
        self.con.close()

    # --------------------------------------------------------------- tezler
    def var_mi(self, tez_id: int) -> bool:
        return self.con.execute("SELECT 1 FROM tezler WHERE id=?", (tez_id,)).fetchone() is not None

    def detayli_mi(self, tez_id: int) -> bool:
        r = self.con.execute("SELECT abstract_original, advisors FROM tezler WHERE id=?", (tez_id,)).fetchone()
        return bool(r and (r["abstract_original"] or r["advisors"] not in (None, "[]")))

    def mevcut_idler(self) -> set[int]:
        return {r[0] for r in self.con.execute("SELECT id FROM tezler")}

    def en_buyuk_id(self) -> int:
        r = self.con.execute("SELECT MAX(id) FROM tezler").fetchone()
        return r[0] or 0

    def kaydet(self, tez: dict, kaynak: str) -> str:
        """Tezi ekler/günceller. 'yeni' | 'guncel' döner."""
        mevcut = self.con.execute("SELECT id FROM tezler WHERE id=?", (tez["id"],)).fetchone()
        degerler = {}
        for a in ALANLAR:
            v = tez.get(a)
            if a in JSON_ALANLAR:
                v = json.dumps(v or [], ensure_ascii=False)
            elif a == "restricted":
                v = int(bool(v))
            degerler[a] = v
        zaman = simdi()
        if mevcut:
            # Boş gelen alan mevcut dolu değeri ezmesin
            def ifade(a: str) -> str:
                bos = "'[]'" if a in JSON_ALANLAR else "''"
                if a == "restricted":
                    return f"{a}=:{a}"
                return f"{a}=COALESCE(NULLIF(:{a},{bos}), {a})"
            sets = ", ".join(ifade(a) for a in ALANLAR if a != "id")
            self.con.execute(
                f"UPDATE tezler SET {sets}, kaynak=:kaynak, son_guncelleme=:z WHERE id=:id",
                {**degerler, "kaynak": kaynak, "z": zaman},
            )
            return "guncel"
        cols = ", ".join(ALANLAR)
        ph = ", ".join(f":{a}" for a in ALANLAR)
        self.con.execute(
            f"INSERT INTO tezler ({cols}, kaynak, ilk_gorulme, son_guncelleme) VALUES ({ph}, :kaynak, :z, :z)",
            {**degerler, "kaynak": kaynak, "z": zaman},
        )
        return "yeni"

    def siniflandirma_yaz(self, tez_id: int, durum: str, puan: int, kategoriler: list, gerekce: list,
                          surum: int, manuel: bool = False, zorla: bool = False):
        if not zorla:
            r = self.con.execute("SELECT manuel FROM tezler WHERE id=?", (tez_id,)).fetchone()
            if r and r["manuel"]:
                return
        self.con.execute(
            "UPDATE tezler SET durum=?, puan=?, kategoriler=?, gerekce=?, siniflandirma_surum=?, manuel=? WHERE id=?",
            (durum, puan, json.dumps(kategoriler, ensure_ascii=False), json.dumps(gerekce, ensure_ascii=False),
             surum, int(manuel), tez_id),
        )

    def tezler(self, durumlar: Iterable[str] | None = None) -> Iterator[dict]:
        q = "SELECT * FROM tezler"
        args: tuple = ()
        if durumlar:
            d = list(durumlar)
            q += f" WHERE durum IN ({','.join('?' * len(d))})"
            args = tuple(d)
        q += " ORDER BY year DESC, id DESC"
        for r in self.con.execute(q, args):
            yield satir_to_dict(r)

    def kisitli_eski(self, gun: int = 90, limit: int = 500) -> list[int]:
        """PDF'i kısıtlı olup uzun süredir kontrol edilmeyen kabul tezleri (ambargo kalkmış olabilir)."""
        q = ("SELECT id FROM tezler WHERE durum='kabul' AND (pdf_url IS NULL OR pdf_url='') "
             "AND julianday('now') - julianday(son_guncelleme) > ? LIMIT ?")
        return [r[0] for r in self.con.execute(q, (gun, limit))]

    # --------------------------------------------------------------- sorgular
    def sorgu_tamam_mi(self, anahtar: str) -> bool:
        r = self.con.execute("SELECT durum FROM sorgular WHERE anahtar=?", (anahtar,)).fetchone()
        return bool(r and r["durum"] == "tamam")

    def sorgu_isaretle(self, anahtar: str, kaynak: str, parametre: dict, bulunan: int, durum: str = "tamam"):
        self.con.execute(
            "INSERT OR REPLACE INTO sorgular VALUES (?,?,?,?,?,?)",
            (anahtar, kaynak, json.dumps(parametre, ensure_ascii=False), bulunan, durum, simdi()),
        )
        self.con.commit()

    def sorgulari_sifirla(self, kaynak: str | None = None):
        if kaynak:
            self.con.execute("DELETE FROM sorgular WHERE kaynak=?", (kaynak,))
        else:
            self.con.execute("DELETE FROM sorgular")
        self.con.commit()

    # --------------------------------------------------------------- durum
    def bilgi_al(self, anahtar: str, varsayilan: str | None = None) -> str | None:
        r = self.con.execute("SELECT deger FROM durum_bilgisi WHERE anahtar=?", (anahtar,)).fetchone()
        return r["deger"] if r else varsayilan

    def bilgi_yaz(self, anahtar: str, deger: str):
        self.con.execute("INSERT OR REPLACE INTO durum_bilgisi VALUES (?,?)", (anahtar, deger))
        self.con.commit()

    def calisma_baslat(self, komut: str) -> int:
        cur = self.con.execute("INSERT INTO calismalar (baslangic, komut) VALUES (?,?)", (simdi(), komut))
        self.con.commit()
        return cur.lastrowid

    def calisma_bitir(self, cid: int, yeni: int, guncellenen: int, kabul: int, notlar: str = ""):
        self.con.execute(
            "UPDATE calismalar SET bitis=?, yeni=?, guncellenen=?, kabul=?, notlar=? WHERE id=?",
            (simdi(), yeni, guncellenen, kabul, notlar, cid),
        )
        self.con.commit()

    def istatistik(self) -> dict:
        c = self.con
        d = {r[0] or "sınıflanmamış": r[1] for r in c.execute("SELECT durum, COUNT(*) FROM tezler GROUP BY durum")}
        kat: dict[str, int] = {}
        for (k,) in c.execute("SELECT kategoriler FROM tezler WHERE durum='kabul'"):
            for x in json.loads(k or "[]"):
                kat[x] = kat.get(x, 0) + 1
        son = c.execute("SELECT * FROM calismalar ORDER BY id DESC LIMIT 5").fetchall()
        return {"durum": d, "kategori": kat, "toplam": sum(d.values()),
                "son_calismalar": [dict(r) for r in son]}

    def commit(self):
        self.con.commit()


def satir_to_dict(r: sqlite3.Row) -> dict:
    d = dict(r)
    for a in JSON_ALANLAR:
        if a in d and isinstance(d[a], str):
            try:
                d[a] = json.loads(d[a])
            except json.JSONDecodeError:
                d[a] = []
    d["restricted"] = bool(d.get("restricted"))
    return d
