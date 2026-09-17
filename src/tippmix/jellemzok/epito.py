"""3. lépés — Feature-építés JÖVŐBE LÁTÁS NÉLKÜL.

AZ ALAPSZABÁLY: minden jellemzőt úgy kell kiszámolni, hogy KIZÁRÓLAG a meccs
kezdése előtti adatokat használja.

Ez élesben triviálisan teljesül, de a backtesztben nagyon könnyű elrontani,
és ha elrontod, a backteszt csodálatos eredményt ad, élesben meg buksz.

EZÉRT: ugyanaz a kódfüggvény építi a jellemzőket élesben és backtesztben,
egyetlen `asof_utc` paraméterrel. Élesben `asof_utc = most`, backtesztben a
meccs kezdési időpontja.

Konkrét tiltások:
  - Nem használható a végső tabellaállás, csak az asof-ig felhalmozott.
  - Nem használható a szezon egészére számolt csapaterősség, csak a gördülő
    ablak.
  - A modellparamétereket a backtesztben MINDEN FORDULÓRA újra kell
    illeszteni az addigi adatokból.

VÁZ: a függvények szignatúrája végleges, a törzs még nincs megírva.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from tippmix.kozos.naplo import naplo
from tippmix.kozos.tipusok import Esemeny

log = naplo(__name__)


def futball_jellemzok(esemeny: Esemeny, asof_utc: datetime) -> pd.Series:
    """Futball-jellemzők egy meccsre, az asof időpontig ismert adatokból.

    Jellemzők (spec 3. lépés):
      - lőtt/kapott gól hazai pályán (utolsó 3 szezon, idősúlyozva)
      - lőtt/kapott gól idegenben (ugyanaz)
      - xG for / xG against (utolsó 10 meccs, ahol elérhető)
      - ClubElo érték (az asof-ra)
      - pihenőnapok száma
      - liga átlagos gólszáma (aktuális szezon eddigi része)

    Args:
        asof_utc: EZ A LEGFONTOSABB PARAMÉTER. Semmi nem használható, ami
            ennél későbbi.
    """
    raise NotImplementedError("3. lépés — a Fázis 2-ben készül el")


def kosar_jellemzok(esemeny: Esemeny, asof_utc: datetime) -> pd.Series:
    """Kosár-jellemzők egy meccsre, az asof időpontig ismert adatokból.

    Jellemzők (spec 3. lépés):
      - offenzív/defenzív rating (utolsó 20 meccs, súlyozva, 100 birtoklásra)
      - pace (birtoklás/meccs, utolsó 20 meccs)
      - Elo
      - back-to-back jelző
      - utazás (hazai/idegen, időzóna-váltás)
      - pihenőnapok
    """
    raise NotImplementedError("3. lépés — a Fázis 7-ben készül el")


def adatelegsegesseg(esemeny: Esemeny, asof_utc: datetime, min_meccs: int) -> bool:
    """Van-e elég adat mindkét csapatra.

    Ha bármelyik csapatnak kevesebb mint `min_meccs` meccse van, az esemény
    KIESIK `KEVES_ADAT` okkal.

    Szezonelején ezért hetekig kevés tipp lesz — ez HELYES VISELKEDÉS, nem hiba.
    """
    raise NotImplementedError("3. lépés — a Fázis 2-ben készül el")
