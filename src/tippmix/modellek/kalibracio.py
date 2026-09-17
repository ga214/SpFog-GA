"""6. lépés — Kalibráció és piaci zsugorítás.

"Ez a két művelet a rendszer legfontosabb része, és pont ez hiányzik a
legtöbb amatőr fogadási modellből." (spec 6. lépés)

KALIBRÁCIÓ
    A modell nyers kimenete lehet szisztematikusan torz: pl. amikor 70%-ot
    mond, a valóságban csak 64%-ban jön be. Ezt méri és javítja a kalibráció.
    Módszer: izotonikus regresszió, a backteszt validációs szeletén illesztve,
    PIACTÍPUSONKÉNT KÜLÖN.
    Ellenőrzés: kalibrációs görbe és Brier-pontszám. Ha a görbe nem közelíti
    az átlót, a modell nem használható élesben.

PIACI ZSUGORÍTÁS
    "Ez a legfontosabb pont az egész dokumentumban." A fogadóiroda ára
    rengeteg információt tartalmaz, amit a mi modellünk nem lát: sérüléshírek,
    fogadói pénzáramlás, taktikai hírek. AZ ESETEK NAGY RÉSZÉBEN A PIACNAK VAN
    IGAZA, NEM NEKÜNK.

        p_végleges = w × p_kalibrált + (1 - w) × p_piac_fair

    A w-t NEM találjuk ki: a backteszt adja meg, a legjobb CLV alapján.
    A 0.35 csak indulóérték.

    A ZSUGORÍTÁS KÖVETKEZMÉNYE, AMIT EL KELL FOGADNI: sokkal kevesebb tipp
    lesz, mint amennyit egy zsugorítás nélküli rendszer adna. Ez nem hiba,
    hanem ez a védelem a hamis élek ellen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from tippmix.kozos.naplo import naplo

log = naplo(__name__)


# =============================================================================
# Piaci zsugorítás — MEGÍRVA (egyszerű képlet, tesztelhető)
# =============================================================================


def zsugorit(p_kalibralt: float, p_piac_fair: float, w: float) -> float:
    """A modell és a piac keveréke: a végleges valószínűség.

        p_végleges = w × p_kalibrált + (1 - w) × p_piac_fair

    Args:
        p_kalibralt: a modell kalibrált valószínűsége [0, 1]
        p_piac_fair: a Tippmix szorzójából vig nélkül számolt valószínűség
        w: a modellbe vetett bizalom [0, 1]
            0    = teljesen a piacot követjük, sosem lesz tipp
            0.35 = kiindulási érték: a modell a piactól való eltérés
                   harmadát viszi át
            1    = csak a modell számít, a piacot figyelmen kívül hagyjuk

    Returns:
        A végleges valószínűség [0, 1]

    Raises:
        ValueError: érvénytelen bemenet
    """
    if not 0.0 <= p_kalibralt <= 1.0:
        raise ValueError(f"p_kalibralt kívül esik a [0,1] tartományon: {p_kalibralt}")
    if not 0.0 <= p_piac_fair <= 1.0:
        raise ValueError(f"p_piac_fair kívül esik a [0,1] tartományon: {p_piac_fair}")
    if not 0.0 <= w <= 1.0:
        raise ValueError(f"w kívül esik a [0,1] tartományon: {w}")

    return w * p_kalibralt + (1.0 - w) * p_piac_fair


def brier_pontszam(p_becsult: np.ndarray, tenyleges: np.ndarray) -> float:
    """Brier-pontszám: az átlagos négyzetes eltérés. Kisebb a jobb.

    A leállítási feltétel ezt figyeli: ha két hétig romlik, a modell elavult.
    """
    p = np.asarray(p_becsult, dtype=float)
    y = np.asarray(tenyleges, dtype=float)
    if p.shape != y.shape:
        raise ValueError(f"Eltérő alak: {p.shape} vs {y.shape}")
    if p.size == 0:
        raise ValueError("Üres bemenet a Brier-pontszámhoz")
    return float(np.mean((p - y) ** 2))


# =============================================================================
# Kalibráció — VÁZ (a backteszt validációs szeletét igényli)
# =============================================================================


class Kalibrator(Protocol):
    """Egy illesztett kalibrációs leképezés: p_nyers → p_kalibrált."""

    def __call__(self, p_nyers: float) -> float: ...


@dataclass(frozen=True, slots=True)
class KalibracioEredmeny:
    """Egy piactípus kalibrációja, minőségi mutatókkal."""

    piac_kod: str
    minta_db: int
    brier_elotte: float
    brier_utana: float
    hasznalhato: bool  # a kalibrációs görbe közelíti-e az átlót


def izotonikus_illesztes(
    p_nyers: np.ndarray, tenyleges: np.ndarray, piac_kod: str
) -> tuple[Kalibrator, KalibracioEredmeny]:
    """Izotonikus regresszió illesztése egy piactípusra.

    Bemenet: több ezer múltbeli meccs p_nyers értéke és a tényleges kimenetel
    (0/1), a backteszt validációs szeletéről.
    """
    raise NotImplementedError("6. lépés — a Fázis 3-ban készül el")


def kalibracios_gorbe(
    p_becsult: np.ndarray, tenyleges: np.ndarray, kosarak: int = 10
) -> tuple[np.ndarray, np.ndarray]:
    """Kalibrációs görbe pontjai: (átlagos becslés, tényleges gyakoriság).

    Ha a görbe nem közelíti az átlót, a modell nem használható élesben.
    """
    raise NotImplementedError("6. lépés — a Fázis 3-ban készül el")


def optimalis_w(
    p_kalibralt: np.ndarray,
    p_fair: np.ndarray,
    odds: np.ndarray,
    zaro_odds: np.ndarray,
    w_racs: np.ndarray | None = None,
) -> float:
    """A zsugorítási súly meghatározása a validációs időszak legjobb CLV-je alapján.

    "A w-t nem én találom ki, a backteszt adja meg." (spec 6. lépés)
    """
    raise NotImplementedError("6. lépés — a Fázis 3-ban készül el")
