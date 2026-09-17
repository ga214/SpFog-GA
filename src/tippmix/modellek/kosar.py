"""5. lépés — Kosármodell.

Kosárban a Poisson nem működik (túl sok pont), helyette KÉT NORMÁLIS
ELOSZLÁST becslünk: a pontkülönbségét és az összpontszámét.

A becslés menete (spec 5. lépés):
  1. ORtg (szerzett pont 100 birtoklásra) és DRtg (kapott pont 100
     birtoklásra) mindkét csapatra, a liga átlagához viszonyítva, az utolsó
     20 meccsből súlyozva.
  2. pace = (pace_hazai + pace_vendég) / 2, liga-átlaghoz igazítva.
  3. pont_hazai  = (ORtg_hazai  + DRtg_vendég - liga_átlag) / 100 × pace + hazai_előny/2
     pont_vendég = (ORtg_vendég + DRtg_hazai  - liga_átlag) / 100 × pace - hazai_előny/2
  4. Korrekciók: back-to-back, hosszú utazás, kiesett kulcsjátékos.
  5. várható_margó = pont_hazai - pont_vendég
     várható_összpont = pont_hazai + pont_vendég

FIGYELEM — BLOKKOLÓ NYITOTT KÉRDÉS:

A σ_margó és σ_össz értékét a specifikáció szándékosan NEM adja meg:
"nem találom ki fejből... a backtesztből, a modell hibáinak tényleges
szórásából kell megbecsülni, ligánként külön (az NBA és az EuroLeague nem
ugyanaz). AMÍG EZ NINCS MEG, A KOSÁRMODELL NEM AD JAVASLATOT."

Ezért a `kosar_aktiv()` addig False-t ad vissza, amíg a szórásparaméterek
nincsenek kalibrálva. Lásd docs/OPEN_QUESTIONS.md.

Továbbá: a spec 3. pontjában a `liga_átlag` pontos definíciója (átlagos ORtg?
átlagos ORtg+DRtg?) nincs megadva — ezt a Fázis 7 elején tisztázni kell.

VÁZ: a függvények szignatúrája végleges, a törzs még nincs megírva.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from tippmix.kozos.naplo import naplo

log = naplo(__name__)


@dataclass(frozen=True, slots=True)
class KosarParameterek:
    """Egy kosárliga illesztett paraméterei."""

    liga_kod: str
    illesztes_idopont_utc: datetime
    liga_atlag_ortg: float
    liga_atlag_pace: float
    hazai_elony: float
    # A két kritikus szórásparaméter. None = még nincs kalibrálva
    # → a modell nem ad javaslatot.
    sigma_margo: float | None
    sigma_ossz: float | None
    b2b_bunteto_pont: float
    tanito_meccs_db: int


def kosar_aktiv(par: KosarParameterek) -> bool:
    """Adhat-e a kosármodell javaslatot.

    False, amíg a σ_margó és σ_össz nincs backtesztből kalibrálva.
    Ez SZÁNDÉKOS kapu, nem hiányzó funkció.
    """
    return par.sigma_margo is not None and par.sigma_ossz is not None


def illeszt(meccsek: pd.DataFrame, liga_kod: str, asof_utc: datetime) -> KosarParameterek:
    """Kosárparaméterek becslése az asof-ig ismert meccsekből."""
    raise NotImplementedError("5. lépés — a Fázis 7-ben készül el")


def varhato_pontok(par: KosarParameterek, jellemzok: pd.Series) -> tuple[float, float]:
    """(pont_hazai, pont_vendég) a spec 3. pontja szerint, korrekciókkal."""
    raise NotImplementedError("5. lépés — a Fázis 7-ben készül el")


def piac_valoszinusegek(
    par: KosarParameterek, varhato_margo: float, varhato_ossz: float, vonal: float
) -> dict[str, float]:
    """Piaci valószínűségek a két normális eloszlásból.

        P(hazai fedi a -X hendikepet) = 1 - Φ((X - várható_margó) / σ_margó)
        P(összpont > T)               = 1 - Φ((T - várható_összpont) / σ_össz)
        P(hazai nyer)                 = 1 - Φ((0 - várható_margó) / σ_margó)

    Raises:
        ModellHiba: ha a szórásparaméterek nincsenek kalibrálva
    """
    raise NotImplementedError("5. lépés — a Fázis 7-ben készül el")


def sigma_becsles(backteszt_hibak: pd.DataFrame, liga_kod: str) -> tuple[float, float]:
    """A σ_margó és σ_össz becslése a backteszt tényleges hibáiból.

    EZT KELL ELŐSZÖR ELVÉGEZNI, mielőtt a kosármodell élesedhet.

    Returns:
        (sigma_margo, sigma_ossz)
    """
    raise NotImplementedError("5. lépés — a Fázis 7-ben készül el")
