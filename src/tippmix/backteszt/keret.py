"""Walk-forward backteszt-keretrendszer.

"A 2. és 3. fázis a lényeg. Ha ezeken átjutunk és a backteszt nem mutat
pozitív CLV-t, akkor a 4-6. fázist nem érdemes megépíteni ebben a formában.
Jobb ezt a 2. héten megtudni, mint a 8-on." (spec, Fejlesztési sorrend)

AZ ALAPSZABÁLY, AMI MINDENT ELDÖNT:

Ugyanaz a kódfüggvény építi a jellemzőket élesben és backtesztben, egyetlen
`asof_utc` paraméterrel. A modellparamétereket MINDEN FORDULÓRA újra kell
illeszteni az addigi adatokból. Ez lassabb, de ez az egyetlen becsületes
módszer.

Ha ezt elrontod, a backteszt csodálatos eredményt ad, élesben meg buksz.

A FŐ MÉRCE A CLV, NEM A P&L:
  - a nyereség rövid távon szinte teljesen a szerencsén múlik
  - a CLV-hez jóval kevesebb minta kell: pár száz fogadáson már értelmezhető
  - a 3%-os ROI statisztikai igazolásához n ≈ 4400 fogadás kellene

A CLV-t a Pinnacle záró vonalához mérjük (football-data.co.uk PSCH/PSCD/PSCA
oszlopok), mert az a legélesebb, legalacsonyabb margójú referencia.

TELJESÍTMÉNY: a backteszt több százezer sort olvas. A Supabase az
igazságforrás, de a backteszt egyszer lehúzza az adatot lokális
Parquet-cache-be (data/cache/), és onnantól lokálisan olvas. A cache a
.gitignore-ban van.

VÁZ: a függvények szignatúrája végleges, a törzs még nincs megírva.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from tippmix.kozos.naplo import naplo

log = naplo(__name__)


@dataclass(frozen=True, slots=True)
class BacktesztEredmeny:
    """Egy backteszt-futás eredménye."""

    fogadas_db: int
    osszes_tet: float
    nyereseg: float
    roi: float
    atlag_clv: float
    pozitiv_clv_arany: float
    brier: float
    max_drawdown: float
    parameterek: dict


def walk_forward(
    kezdet: date,
    veg: date,
    ligak: list[str],
    ujrafittelés_naponta: int = 7,
) -> BacktesztEredmeny:
    """Walk-forward backteszt.

    Minden fordulóra:
      1. Illeszd a modellt KIZÁRÓLAG az addigi adatokból
      2. Építsd a jellemzőket asof_utc = a meccs kezdése
      3. Számold a valószínűségeket, a vig-mentes fair árat, az élt
      4. Alkalmazd a döntési fát és a tétezést
      5. Rögzítsd a CLV-t a Pinnacle záró vonalához

    Args:
        ujrafittelés_naponta: hány naponta illesszük újra a modellt.
            A specifikáció "minden fordulóra" ír, ez a gyakorlati közelítés;
            a végleges értéket mérni kell.
    """
    raise NotImplementedError("Backteszt — a Fázis 2-ben készül el")


def parameter_kereses(
    kezdet: date,
    veg: date,
    ligak: list[str],
    w_racs: list[float],
    xi_racs: list[float],
) -> pd.DataFrame:
    """A zsugorítási súly (w) és az időbeli felejtés (ξ) keresése.

    "A w-t nem én találom ki, a backteszt adja meg: azt az értéket keressük,
    ami a validációs időszakon a legjobb CLV-t hozza."

    FIGYELEM: a keresést a VALIDÁCIÓS szeleten kell futtatni, és a végleges
    értékelést egy külön, érintetlen teszt-szeleten. Különben a paraméterek
    ráilleszkednek a zajra.
    """
    raise NotImplementedError("Backteszt — a Fázis 3-ban készül el")


def cache_feltoltes(ligak: list[str], szezonok: list[str]) -> None:
    """Az adat lehúzása Supabase-ből lokális Parquet-cache-be.

    A backteszt több százezer sort olvas — ezt hálózaton keresztül nem
    érdemes. A Supabase marad az igazságforrás, ez csak gyorsítótár.
    """
    raise NotImplementedError("Backteszt — a Fázis 1-ben készül el")
