"""4. lépés — Futballmodell (Dixon-Coles).

AZ ALAPGONDOLAT: a hazai és a vendég gólszáma két (majdnem) független
Poisson-eloszlású szám. Minden csapatnak van támadó- és védőereje, és van
általános hazaipálya-előny:

    log(λ_hazai)  = támadás[hazai]  + védelem[vendég] + hazai_előny
    log(λ_vendég) = támadás[vendég] + védelem[hazai]

A paraméterek ligánként illesztve, IDŐSÚLYOZVA: a súly exp(-ξ · napok),
ahol ξ = 0.0035 (kb. fél év alatt felezi a súlyt). A ξ végleges értékét a
backteszt adja.

DIXON-COLES KORREKCIÓ: a tiszta Poisson alulbecsli a nagyon alacsony
eredményeket (0-0, 1-0, 0-1, 1-1). A korrekció ezt a négy cellát megszorozza
egy τ(x, y, λ_h, λ_v, ρ) tényezővel. A ρ az eredeti tanulmányban ≈ −0,13 volt
angol adatokra; nálunk LIGÁNKÉNT ÚJRAILLESZTJÜK.

Hivatkozás: Dixon, M.J. & Coles, S.G. (1997), "Modelling Association Football
Scores and Inefficiencies in the Football Betting Market", JRSS-C 46(2):265-280.

VÁZ: a függvények szignatúrája végleges, a törzs még nincs megírva.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from tippmix.kozos.naplo import naplo

log = naplo(__name__)

# Az eredménymátrix mérete: 0-10 gól mindkét oldalon (spec 4. lépés)
MATRIX_MERET = 11


@dataclass(frozen=True, slots=True)
class DixonColesParameterek:
    """Egy liga illesztett paraméterei."""

    liga_kod: str
    illesztes_idopont_utc: datetime
    tamadas: dict[str, float]
    vedelem: dict[str, float]
    hazai_elony: float
    rho: float
    xi: float
    tanito_meccs_db: int
    konvergalt: bool
    log_likelihood: float

    def kor_nap(self, most: datetime) -> float:
        """Hány napos az illesztés. A MODELL_ELAVULT kapu ezt nézi."""
        return (most - self.illesztes_idopont_utc).total_seconds() / 86400


def tau(x: int, y: int, lambda_h: float, lambda_v: float, rho: float) -> float:
    """A Dixon-Coles korrekciós tényező a négy alacsony eredményre.

    Csak a (0,0), (0,1), (1,0), (1,1) cellákra tér el 1-től.
    """
    raise NotImplementedError("4. lépés — a Fázis 2-ben készül el")


def idosuly(meccs_datum: datetime, asof_utc: datetime, xi: float) -> float:
    """Időbeli súly: exp(-ξ · eltelt_napok).

    Egy tavalyi meccs kevesebbet számít, mint a múlt hetiek.
    """
    raise NotImplementedError("4. lépés — a Fázis 2-ben készül el")


def illeszt(
    meccsek: pd.DataFrame, liga_kod: str, asof_utc: datetime, xi: float
) -> DixonColesParameterek:
    """Dixon-Coles illesztés egy ligára, az asof időpontig ismert meccsekből.

    A backtesztben MINDEN FORDULÓRA újra kell hívni — ez lassabb, de ez az
    egyetlen becsületes módszer.

    Raises:
        ModellHiba: az optimalizálás nem konvergált (ILLESZTES_SIKERTELEN)
    """
    raise NotImplementedError("4. lépés — a Fázis 2-ben készül el")


def lambdak(par: DixonColesParameterek, hazai_id: str, vendeg_id: str) -> tuple[float, float]:
    """A két várható gólszám egy meccsre."""
    raise NotImplementedError("4. lépés — a Fázis 2-ben készül el")


def eredmenymatrix(lambda_h: float, lambda_v: float, rho: float) -> np.ndarray:
    """11x11-es mátrix: P(hazai i gólt lő ÉS vendég j gólt lő).

    Dixon-Coles korrekcióval, 1-re normalizálva.
    """
    raise NotImplementedError("4. lépés — a Fázis 2-ben készül el")


def piac_valoszinusegek(matrix: np.ndarray) -> dict[str, float]:
    """Piaci valószínűségek az eredménymátrixból — egyszerű összeadás.

    Returns:
        {"1": p, "X": p, "2": p, "OU25_Tobb": p, "OU25_Kevesebb": p,
         "BTTS_Igen": p, "BTTS_Nem": p}

    Első verzióban csak az 1X2 és az OU25 aktív (config/ligak.yaml).
    """
    raise NotImplementedError("4. lépés — a Fázis 2-ben készül el")
