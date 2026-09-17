"""Történelmi adatok letöltése a modellezéshez és a backteszthez.

Források (kutatási jelentés 2-3. szakasz):

  FUTBALL
    football-data.co.uk  — eredmény + NYITÓ ÉS ZÁRÓ odds, ~22 liga.
                           Ez az EGYETLEN ingyenes forrás, ami eredményt ÉS
                           záró oddsot egyben ad → a CLV-mérés alapja.
    Understat            — xG 2014/15-től, 6 liga
    ClubElo              — napi Elo-értékelés, CSV API
    (mind elérhető a `soccerdata` wrapperen keresztül)

  KOSÁR
    nba_api              — FIGYELEM: a stats.nba.com blokkolja az
                           adatközponti IP-ket → GitHub Actionsből
                           valószínűleg nem megy. Tartalék:
                           Basketball-Reference.
    euroleague-api       — EuroLeague/EuroCup
    sportsbookreviewsonline.com — történelmi NBA záró odds (Excel)

VÁZ: a függvények szignatúrája végleges, a törzs még nincs megírva.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from tippmix.kozos.naplo import naplo

log = naplo(__name__)


def footballdata_letoltes(liga_kod: str, szezonok: list[str]) -> pd.DataFrame:
    """football-data.co.uk CSV letöltése egy ligára, több szezonra.

    A záró oddsokat "C" jelöli az oszlopnevekben (B365CH, PSCH), a Pinnacle
    ázsiai hendikepet PAHH/PAHA. A CLV-t a Pinnacle záró vonalához mérjük,
    mert az a legélesebb, legalacsonyabb margójú referencia.
    """
    raise NotImplementedError("Fázis 1-ben készül el")


def understat_xg_letoltes(understat_liga: str, szezonok: list[str]) -> pd.DataFrame:
    """Understat xG-adat letöltése."""
    raise NotImplementedError("Fázis 1-ben készül el")


def clubelo_letoltes(datum: date) -> pd.DataFrame:
    """ClubElo napi pillanatkép — feature-nek."""
    raise NotImplementedError("Fázis 1-ben készül el")


def nba_meccsek_letoltes(szezonok: list[str]) -> pd.DataFrame:
    """NBA meccsadatok. Adatközponti IP-ről valószínűleg blokkolt."""
    raise NotImplementedError("Fázis 7-ben készül el")


def euroleague_meccsek_letoltes(szezonok: list[str]) -> pd.DataFrame:
    """EuroLeague meccsadatok."""
    raise NotImplementedError("Fázis 7-ben készül el")
