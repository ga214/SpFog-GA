"""Közös adattípusok — a pipeline lépései ezeken keresztül kommunikálnak.

Az adatfolyam a specifikáció 12 lépését követi:

    NyersEsemeny   (1. lépés)  → a Tippmix Pro-ról letöltve
    Esemeny        (2. lépés)  → névillesztéssel, kanonikus azonosítókkal
    Jelolt         (7. lépés)  → esemény × piac × kimenetel, éllel és EV-vel
    Javaslat       (9. lépés)  → túlélő jelölt konkrét tétösszeggel
    Kombinacio     (10. lépés) → 2-3 lábas szelvény
    Kieses                     → egy jelölt kiesése, okkal (naplózáshoz)

Minden osztály fagyasztott (immutable): egy lépés nem módosítja a bemenetét,
hanem újat épít. Ez teszi a pipeline-t visszakövethetővé.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from tippmix.kozos.hibak import KiesesiOk


@dataclass(frozen=True, slots=True)
class NyersEsemeny:
    """1. lépés kimenete: egy Tippmix-esemény egy piaca egy kimenetele.

    A mezők a specifikáció 1. lépésének táblázatából származnak.
    """

    tippmix_event_id: str
    sport: str  # "foci" | "kosar"
    bajnoksag: str  # a Tippmix írásmódja szerint, pl. "Premier League"
    hazai_nev: str  # a Tippmix írásmódja szerint
    vendeg_nev: str
    kezdes_utc: datetime
    piac_nev: str  # "Végeredmény" | "Gólszám 2.5" | ...
    kimenetel_nev: str  # "Hazai" | "Több" | ...
    odds: float
    kotestiltas: bool = False


@dataclass(frozen=True, slots=True)
class Esemeny:
    """2. lépés kimenete: névillesztett esemény.

    Egy `Esemeny` több `NyersEsemeny` sort fog össze (ugyanaz a meccs, több
    piac és kimenetel).
    """

    tippmix_event_id: str
    kanonikus_meccs_id: str
    sport: str
    liga_kod: str  # a league_map.csv szerint, pl. "E0"
    hazai_id: str  # kanonikus, pl. "ENG_ARSENAL"
    vendeg_id: str
    hazai_nev: str  # megjelenítéshez, a Tippmix írásmódja
    vendeg_nev: str
    kezdes_utc: datetime


@dataclass(frozen=True, slots=True)
class Odds:
    """Egy piac egy kimenetelének szorzója, a vig-eltávolítás eredményével.

    A `p_fair` a 7. lépés power-módszerével számolt fair valószínűség.
    A `p_fair_aranyos` a proportional módszer eredménye — referenciaként
    végigszámoljuk, és ha a kettő nagyon eltér, az figyelmeztető jel.
    """

    piac_kod: str  # "1X2" | "OU25" | "TOTAL" | "SPREAD"
    kimenetel: str  # "1" | "X" | "2" | "Tobb" | "Kevesebb" | ...
    odds: float
    vonal: float | None = None  # a hendikep/összpont vonala, ha van
    p_fair: float | None = None
    p_fair_aranyos: float | None = None
    kotestiltas: bool = False


@dataclass(frozen=True, slots=True)
class Jelolt:
    """7. lépés kimenete: esemény × piac × kimenetel, éllel és EV-vel.

    Ez megy be a 8. lépés döntési fájába.
    """

    esemeny: Esemeny
    odds: Odds
    p_modell_nyers: float
    p_kalibralt: float
    p_vegleges: float  # a piaci zsugorítás után (6. lépés)
    edge: float  # p_vegleges - p_fair
    ev: float  # p_vegleges * odds - 1
    referencia_odds: float | None = None
    referencia_p_fair: float | None = None
    hirveto_allapot: str = "nincs_ellenorzes"  # "tiszta" | "veto" | "nincs_ellenorzes"
    indoklas: str = ""  # emberi nyelvű magyarázat az e-mailhez


@dataclass(frozen=True, slots=True)
class Javaslat:
    """9. lépés kimenete: túlélő jelölt konkrét tétösszeggel."""

    jelolt: Jelolt
    kelly_nyers: float  # f*
    kelly_hasznalt: float  # f* × kelly_hányad
    tet_ft: int  # levágva, kerekítve
    lehetseges_nyeremeny_ft: int

    @property
    def esemeny(self) -> Esemeny:
        return self.jelolt.esemeny

    @property
    def odds(self) -> float:
        return self.jelolt.odds.odds


@dataclass(frozen=True, slots=True)
class Kombinacio:
    """10. lépés kimenete: 2-3 lábas szelvény.

    Minden láb önmagában is átment a 8. lépés teljes döntési fáján.
    """

    labak: tuple[Javaslat, ...]
    kombi_odds: float
    kombi_p: float
    kombi_ev: float
    tet_ft: int
    lehetseges_nyeremeny_ft: int


@dataclass(frozen=True, slots=True)
class Kieses:
    """Egy jelölt kiesése a döntési fán, okkal.

    Az e-mail "NEM JAVASOLT, DE MEGVIZSGÁLVA" szakasza ezekből épül:
    a program dolgozott, csak nem talált semmit — nem pedig elromlott.
    """

    tippmix_event_id: str
    hazai_nev: str
    vendeg_nev: str
    piac_kod: str
    kimenetel: str
    ok: KiesesiOk
    reszletek: str = ""


@dataclass(slots=True)
class FutasEredmeny:
    """Egy teljes napi futás eredménye.

    Ez megy a 11. lépésbe (e-mail) és a 12. lépésbe (naplózás).
    Nem fagyasztott: a pipeline lépései töltik fel.
    """

    futas_id: str
    futas_tipusa: str  # "delelott" | "este"
    idopont_utc: datetime
    javaslatok: list[Javaslat] = field(default_factory=list)
    kombinaciok: list[Kombinacio] = field(default_factory=list)
    kiesesek: list[Kieses] = field(default_factory=list)
    ismeretlen_csapatok: list[tuple[str, str, int]] = field(default_factory=list)
    # (tippmix_nev, javasolt_kanonikus_id, fuzzy_pontszam)
    megvizsgalt_esemeny_db: int = 0
    megvizsgalt_piac_db: int = 0
    figyelmeztetesek: list[str] = field(default_factory=list)

    def osszes_tet_ft(self) -> int:
        return sum(j.tet_ft for j in self.javaslatok) + sum(k.tet_ft for k in self.kombinaciok)

    def max_nyeremeny_ft(self) -> int:
        return sum(j.lehetseges_nyeremeny_ft for j in self.javaslatok) + sum(
            k.lehetseges_nyeremeny_ft for k in self.kombinaciok
        )

    def kiesesek_okonkent(self) -> dict[KiesesiOk, int]:
        """Kiesési okok darabszáma, csökkenő sorrendben — az e-mailhez."""
        szamlalo: dict[KiesesiOk, int] = {}
        for k in self.kiesesek:
            szamlalo[k.ok] = szamlalo.get(k.ok, 0) + 1
        return dict(sorted(szamlalo.items(), key=lambda x: x[1], reverse=True))

    def van_javaslat(self) -> bool:
        return bool(self.javaslatok or self.kombinaciok)
