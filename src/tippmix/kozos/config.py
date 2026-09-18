"""Konfiguráció betöltése és validálása.

A `settings.yaml` és a `ligak.yaml` betöltése, séma-ellenőrzéssel. Az
elgépelt vagy hiányzó kulcs itt derül ki, nem futásidőben, három lépéssel
később egy `KeyError`-ral.

SZABÁLY: a kódban sehol nem lehet beégetett szám. Ha egy számra szükség van,
az ide kerül, és innen olvassák.

TITOK: ez a modul YAML-t olvas, ami a repóban van. Titkot SOHA nem olvas —
arra a `titkok.py` való.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from tippmix.kozos.hibak import KonfiguracioHiba

# A projekt gyökere: ez a fájl src/tippmix/kozos/config.py, tehát 3 szint fel.
PROJEKT_GYOKER = Path(__file__).resolve().parents[3]


# =============================================================================
# Séma — a settings.yaml blokkjai
# =============================================================================


class Bankroll(BaseModel):
    induló_ft: int = Field(gt=0)
    aktuális_ft: int = Field(gt=0)


class Tet(BaseModel):
    kelly_hányad: float = Field(gt=0, le=1)
    min_ft: int = Field(gt=0)
    max_ft: int = Field(gt=0)
    max_bankroll_százalék: float = Field(gt=0, le=1)
    kerekítés_ft: int = Field(gt=0)


class NapiLimit(BaseModel):
    max_tipp_db: int = Field(gt=0)
    max_kitettség_bankroll_százalék: float = Field(gt=0, le=1)
    max_kombináció_db: int = Field(ge=0)


class Kuszob(BaseModel):
    min_edge_délelőtt: float = Field(ge=0)
    min_edge_este: float = Field(ge=0)
    min_ev: float = Field(ge=0)
    min_odds: float = Field(gt=1)
    max_odds: float = Field(gt=1)
    max_eltérés_referenciától: float = Field(ge=0)

    @field_validator("max_odds")
    @classmethod
    def max_nagyobb_mint_min(cls, v: float, info: Any) -> float:
        min_odds = info.data.get("min_odds")
        if min_odds is not None and v <= min_odds:
            raise ValueError(f"max_odds ({v}) nem lehet <= min_odds ({min_odds})")
        return v


class Modell(BaseModel):
    zsugorítás_w: float = Field(ge=0, le=1)
    dixon_coles_xi: float = Field(ge=0)
    min_meccs_csapatonként: int = Field(gt=0)
    modell_max_kor_nap: int = Field(gt=0)


class Kombinacio(BaseModel):
    max_láb: int = Field(ge=1)
    min_láb_edge: float = Field(ge=0)
    tét_szorzó: float = Field(gt=0, le=1)


class Futas(BaseModel):
    délelőtt_cet: str
    este_cet: str
    min_perc_kezdésig: int = Field(ge=0)


class Wamp(BaseModel):
    """A Tippmix WAMP-végpont paraméterei (docs/OPEN_QUESTIONS.md NY-11)."""

    url: str
    realm: str
    origin: str
    authid: str
    alprotokoll: str
    eljaras: str
    operator_id: int
    nyelv: str
    max_keret_meret_mb: int = Field(gt=0)
    sport_id: dict[str, int]
    piac_kod: dict[str, str]
    kimenetel_kod: dict[str, str]

    def topic(self, *reszek: str | int) -> str:
        """WAMP-topic összeállítása: /sports/<operátor>/<nyelv>/<részek…>."""
        farok = "/".join(str(r) for r in reszek)
        return f"/sports/{self.operator_id}/{self.nyelv}/{farok}"


class Gyujtes(BaseModel):
    ujraprobalkozas_db: int = Field(gt=0)
    ujraprobalkozas_szunet_mp: int = Field(ge=0)
    keres_idokorlat_mp: int = Field(gt=0)
    keresek_kozti_szunet_mp: float = Field(ge=0)
    user_agent: str
    nyers_mentes_konyvtar: str
    kezi_tartalek_konyvtar: str
    wamp: Wamp


class Nevillesztes(BaseModel):
    alias_csv: str
    liga_csv: str
    javaslat_min_pontszam: int = Field(ge=0, le=100)


class Hirveto(BaseModel):
    hianyzo_forras_kuszob_szorzo: float = Field(ge=1)
    kulcsjatekos_ablak_meccs: int = Field(gt=0)
    kosar_top_k_percatlag: int = Field(gt=0)
    foci_top_k_mezonyjatekos: int = Field(gt=0)


class Platform(BaseModel):
    max_nyeremeny_ft: int = Field(gt=0)
    min_tet_ft: int = Field(gt=0)
    max_tet_ft: int = Field(gt=0)


class Leallitas(BaseModel):
    bankroll_eses_szazalek: float = Field(gt=0, le=1)
    clv_min_minta: int = Field(gt=0)
    adathiany_egymas_utani_futas: int = Field(gt=0)
    brier_romlas_hetek: int = Field(gt=0)


class Ido(BaseModel):
    tarolas_zona: str
    megjelenites_zona: str
    cron_turés_perc: int = Field(gt=0)


class Naplozas(BaseModel):
    szint: str
    formatum: str
    fajl_konyvtar: str
    hibalevel_kuldese: bool


class Adattar(BaseModel):
    backend: str
    cache_konyvtar: str
    cache_max_kor_ora: int = Field(gt=0)


class Tortenelmi(BaseModel):
    szezonok_szama: int = Field(gt=0)
    konyvtar: str
    zaro_odds_iroda: str
    zaro_odds_tartalek: str


class Email(BaseModel):
    felado_nev: str
    smtp_host: str
    smtp_port: int = Field(gt=0)
    targy_elotag: str


class Beallitasok(BaseModel):
    """A teljes settings.yaml, validálva."""

    bankroll: Bankroll
    tét: Tet
    napi_limit: NapiLimit
    küszöb: Kuszob
    modell: Modell
    kombináció: Kombinacio
    futás: Futas
    gyujtes: Gyujtes
    nevillesztes: Nevillesztes
    hirveto: Hirveto
    platform: Platform
    leallitas: Leallitas
    ido: Ido
    naplozas: Naplozas
    adattar: Adattar
    tortenelmi: Tortenelmi
    email: Email

    def tet_plafon_ft(self) -> int:
        """A tényleges tétplafon: a max_ft és a bankroll-százalék közül a szigorúbb.

        Spec 9. lépés: "A max_bankroll_százalék és a max_ft közül mindig a
        szigorúbb nyer." 50 000 Ft bankrollnál a 4% = 2000 Ft, tehát kezdetben
        ez a plafon, nem az 5000 Ft.
        """
        szazalekos = int(self.tét.max_bankroll_százalék * self.bankroll.aktuális_ft)
        return min(self.tét.max_ft, szazalekos)

    def min_edge(self, futas_tipusa: str) -> float:
        """A napszakhoz tartozó minimális él.

        Spec: délelőtt nincs meg a kezdőcsapat, nagyobb a bizonytalanság,
        ezért többet kérünk az élből.
        """
        if futas_tipusa == "delelott":
            return self.küszöb.min_edge_délelőtt
        if futas_tipusa == "este":
            return self.küszöb.min_edge_este
        raise KonfiguracioHiba(
            f"Ismeretlen futástípus: {futas_tipusa!r} (várt: 'delelott' vagy 'este')"
        )


# =============================================================================
# Séma — a ligak.yaml
# =============================================================================


class FutballLiga(BaseModel):
    kod: str
    nev: str
    # A bajnokság neve a Tippmix írásmódja szerint, évad nélkül. None, ha még
    # nem derítettük ki — ilyenkor a liga nem gyűjthető (nem találgatunk).
    tippmix_nev: str | None = None
    orszag: str
    aktiv: bool
    xg_forras: str | None = None
    understat_liga: str | None = None
    # A liga azonosítója a soccerdata wrapperben ("ENG-Premier League").
    # None, ha nem derítettük ki — ilyenkor a liga nem tölthető le.
    soccerdata_liga: str | None = None
    clubelo: bool = False


class KosarLiga(BaseModel):
    kod: str
    nev: str
    tippmix_nev: str | None = None
    aktiv: bool
    stat_forras: str
    adatkozponti_ip_kockazat: bool = False
    tartalek_forras: str | None = None
    tortenelmi_odds_hianyzik: bool = False


class Piac(BaseModel):
    kod: str
    nev: str
    kimenetelek: list[str]
    aktiv: bool


class Piacok(BaseModel):
    futball: list[Piac]
    kosarlabda: list[Piac]


class Ligak(BaseModel):
    """A teljes ligak.yaml, validálva."""

    futball: list[FutballLiga]
    kosarlabda: list[KosarLiga]
    piacok: Piacok

    def aktiv_futball_kodok(self) -> set[str]:
        return {liga.kod for liga in self.futball if liga.aktiv}

    def aktiv_kosar_kodok(self) -> set[str]:
        return {liga.kod for liga in self.kosarlabda if liga.aktiv}

    def aktiv_piacok(self, sport: str) -> set[str]:
        """Egy sport aktív piackódjai.

        A döntési fa 7. pontja (NEM_TAMOGATOTT_PIAC) ezt használja.
        """
        if sport == "foci":
            piacok = self.piacok.futball
        elif sport == "kosar":
            piacok = self.piacok.kosarlabda
        else:
            raise KonfiguracioHiba(f"Ismeretlen sport: {sport!r} (várt: 'foci' vagy 'kosar')")
        return {p.kod for p in piacok if p.aktiv}


# =============================================================================
# Betöltés
# =============================================================================


def _yaml_olvas(utvonal: Path) -> dict[str, Any]:
    if not utvonal.exists():
        raise KonfiguracioHiba(f"Hiányzó konfigurációs fájl: {utvonal}")
    try:
        with utvonal.open(encoding="utf-8") as f:
            tartalom = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise KonfiguracioHiba(f"Érvénytelen YAML: {utvonal} — {e}") from e
    if not isinstance(tartalom, dict):
        raise KonfiguracioHiba(f"A {utvonal} gyökere nem szótár, hanem {type(tartalom).__name__}")
    return tartalom


@lru_cache(maxsize=1)
def beallitasok(utvonal: Path | None = None) -> Beallitasok:
    """A settings.yaml betöltve és validálva. Az eredmény gyorsítótárazott."""
    ut = utvonal or PROJEKT_GYOKER / "config" / "settings.yaml"
    nyers = _yaml_olvas(ut)
    try:
        return Beallitasok.model_validate(nyers)
    except Exception as e:
        raise KonfiguracioHiba(f"Érvénytelen konfiguráció a {ut} fájlban:\n{e}") from e


@lru_cache(maxsize=1)
def ligak(utvonal: Path | None = None) -> Ligak:
    """A ligak.yaml betöltve és validálva. Az eredmény gyorsítótárazott."""
    ut = utvonal or PROJEKT_GYOKER / "config" / "ligak.yaml"
    nyers = _yaml_olvas(ut)
    try:
        return Ligak.model_validate(nyers)
    except Exception as e:
        raise KonfiguracioHiba(f"Érvénytelen ligakonfiguráció a {ut} fájlban:\n{e}") from e


def gyoker_ut(*reszek: str) -> Path:
    """Projekt-gyökérhez képesti abszolút útvonal.

    Használat: gyoker_ut("data", "raw") → C:/temp/Sportfogadas/data/raw
    """
    return PROJEKT_GYOKER.joinpath(*reszek)
