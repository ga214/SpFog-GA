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

from tippmix.kozos.hibak import ModellHiba
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


# A kalibrációhoz szükséges legkisebb mintaszám. Ennél kevesebből a görbe a
# zajra illeszkedne, és rosszabbá tenné a becslést, mint amilyen volt.
MIN_KALIBRACIOS_MINTA = 200


def izotonikus_illesztes(
    p_nyers: np.ndarray, tenyleges: np.ndarray, piac_kod: str
) -> tuple[Kalibrator, KalibracioEredmeny]:
    """Izotonikus regresszió illesztése egy piactípusra.

    Bemenet: több ezer múltbeli meccs p_nyers értéke és a tényleges kimenetel
    (0/1), a backteszt validációs szeletéről.

    Az izotonikus regresszió monoton leképezést tanul: ha a modell azt mondta
    "60%", de az ilyen esetek valójában csak 52%-ban jöttek be, a kalibrátor
    ezt lejjebb húzza. A monotonitás azt garantálja, hogy a sorrendet nem
    forgatja fel — csak a szinteket igazítja.

    Raises:
        ModellHiba: túl kevés minta a megbízható kalibrációhoz.
    """
    from sklearn.isotonic import IsotonicRegression

    p_nyers = np.asarray(p_nyers, dtype=float)
    tenyleges = np.asarray(tenyleges, dtype=float)
    if p_nyers.shape != tenyleges.shape:
        raise ValueError(f"Eltérő alak: {p_nyers.shape} vs {tenyleges.shape}")
    if p_nyers.size < MIN_KALIBRACIOS_MINTA:
        raise ModellHiba(
            f"{piac_kod}: {p_nyers.size} minta kevés a kalibrációhoz "
            f"(legalább {MIN_KALIBRACIOS_MINTA} kell)."
        )

    modell = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    modell.fit(p_nyers, tenyleges)

    def kalibrator(p: float) -> float:
        return float(modell.predict([p])[0])

    brier_elotte = brier_pontszam(p_nyers, tenyleges)
    brier_utana = brier_pontszam(modell.predict(p_nyers), tenyleges)

    return kalibrator, KalibracioEredmeny(
        piac_kod=piac_kod,
        minta_db=int(p_nyers.size),
        brier_elotte=brier_elotte,
        brier_utana=brier_utana,
        # In-sample a kalibráció mindig javít; a "használható" az, ha nem
        # ront. A valódi próba a külön teszt-szelet.
        hasznalhato=brier_utana <= brier_elotte,
    )


def kalibracios_gorbe(
    p_becsult: np.ndarray, tenyleges: np.ndarray, kosarak: int = 10
) -> tuple[np.ndarray, np.ndarray]:
    """Kalibrációs görbe pontjai: (átlagos becslés, tényleges gyakoriság).

    Ha a görbe nem közelíti az átlót, a modell nem használható élesben.

    A kosarak egyenlő elemszámúak (kvantilis alapú), nem egyenlő szélességűek:
    így a ritkán előforduló szélső valószínűségek nem adnak zajos pontokat.
    """
    p_becsult = np.asarray(p_becsult, dtype=float)
    tenyleges = np.asarray(tenyleges, dtype=float)
    if p_becsult.size == 0:
        return np.array([]), np.array([])

    hatarok = np.quantile(p_becsult, np.linspace(0, 1, kosarak + 1))
    hatarok = np.unique(hatarok)
    if hatarok.size < 2:
        return np.array([p_becsult.mean()]), np.array([tenyleges.mean()])

    besorolas = np.clip(np.digitize(p_becsult, hatarok[1:-1]), 0, hatarok.size - 2)
    becsult_pontok, tenyleges_pontok = [], []
    for kosar in range(hatarok.size - 1):
        maszk = besorolas == kosar
        if maszk.sum() == 0:
            continue
        becsult_pontok.append(float(p_becsult[maszk].mean()))
        tenyleges_pontok.append(float(tenyleges[maszk].mean()))
    return np.array(becsult_pontok), np.array(tenyleges_pontok)


def optimalis_w(
    p_kalibralt: np.ndarray,
    p_fair: np.ndarray,
    odds: np.ndarray,
    zaro_odds: np.ndarray,
    w_racs: np.ndarray | None = None,
) -> float:
    """A zsugorítási súly meghatározása a validációs időszak legjobb CLV-je alapján.

    "A w-t nem én találom ki, a backteszt adja meg." (spec 6. lépés)

    A CLV-t a záró vonalhoz mérjük: egy fogadás akkor jó, ha a záró ár
    alacsonyabb lett, mint amin fogadtunk — vagyis a piac utólag felénk
    mozdult.
    """
    p_kalibralt = np.asarray(p_kalibralt, dtype=float)
    p_fair = np.asarray(p_fair, dtype=float)
    odds = np.asarray(odds, dtype=float)
    zaro_odds = np.asarray(zaro_odds, dtype=float)
    if w_racs is None:
        w_racs = np.linspace(0.0, 1.0, 21)

    legjobb_w, legjobb_clv = float(w_racs[0]), -np.inf
    for w in w_racs:
        p_vegleges = np.array(
            [zsugorit(pk, pf, float(w)) for pk, pf in zip(p_kalibralt, p_fair, strict=True)]
        )
        # Csak ott fogadnánk, ahol a zsugorítás után is van él.
        valasztott = p_vegleges > p_fair
        if not valasztott.any():
            continue
        clv = float(np.mean(odds[valasztott] / zaro_odds[valasztott] - 1.0))
        if clv > legjobb_clv:
            legjobb_w, legjobb_clv = float(w), clv
    return legjobb_w
