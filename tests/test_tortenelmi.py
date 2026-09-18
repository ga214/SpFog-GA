"""Fázis 1 — a történelmi adatletöltés tesztjei.

Hálózat NÉLKÜL: a football-data.co.uk válaszának szerkezetét rögzített minta
képviseli. Amit védenek:

  - a szezonkódok számítása (az augusztusi fordulóval),
  - a záró odds kiolvasása és a tartalék-irodára esés,
  - a hiányos meccsek eldobása.

A záró odds a CLV alapja: ha rosszul olvassuk ki, a backteszt egy nem létező
referenciához mér, és a hiba csendben marad.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from tippmix.gyujtes import tortenelmi
from tippmix.kozos.hibak import AdatgyujtesHiba

# ---------------------------------------------------------------------------
# Szezonkódok
# ---------------------------------------------------------------------------


def test_szezon_kodok_augusztus_utan_az_uj_szezon() -> None:
    """Augusztustól már az új szezon fut."""
    assert tortenelmi.szezon_kodok(2, ma=date(2026, 9, 18)) == ["2526", "2627"]


def test_szezon_kodok_augusztus_elott_meg_a_regi() -> None:
    assert tortenelmi.szezon_kodok(2, ma=date(2026, 5, 1)) == ["2425", "2526"]


def test_szezon_kodok_evszazadfordulon() -> None:
    """A kétjegyű forma a 99/00 fordulón sem törhet el."""
    assert tortenelmi.szezon_kodok(1, ma=date(1999, 9, 1)) == ["9900"]


def test_szezon_kodok_novekvo_sorrendben() -> None:
    kodok = tortenelmi.szezon_kodok(4, ma=date(2026, 9, 18))
    assert kodok == sorted(kodok)
    assert len(kodok) == 4


# ---------------------------------------------------------------------------
# Normalizálás
# ---------------------------------------------------------------------------


def _nyers(**felulir) -> pd.DataFrame:
    """A football-data.co.uk tábláját utánozza, MultiIndexszel együtt."""
    adat = {
        "date": ["2024-08-16", "2024-08-17"],
        "home_team": ["Brentford", "Arsenal"],
        "away_team": ["Chelsea", "Spurs"],
        "FTHG": [2, 1],
        "FTAG": [0, 1],
        "PSCH": [2.50, 1.80],
        "PSCD": [3.40, 3.60],
        "PSCA": [2.90, 4.50],
        "PC>2.5": [1.90, 2.05],
        "PC<2.5": [1.95, 1.80],
        "B365CH": [2.45, 1.78],
        "B365CD": [3.35, 3.55],
        "B365CA": [2.85, 4.40],
        "B365C>2.5": [1.88, 2.00],
        "B365C<2.5": [1.92, 1.78],
    }
    adat.update(felulir)
    tabla = pd.DataFrame(adat)
    tabla.index = pd.MultiIndex.from_tuples(
        [("ENG-Premier League", "2425", f"g{i}") for i in range(len(tabla))],
        names=["league", "season", "game"],
    )
    return tabla


def test_normalizal_alapmezok() -> None:
    ki = tortenelmi._normalizal(_nyers(), "E0")
    assert list(ki.columns)[:7] == [
        "liga_kod",
        "szezon",
        "datum",
        "hazai",
        "vendeg",
        "hazai_gol",
        "vendeg_gol",
    ]
    assert set(ki["liga_kod"]) == {"E0"}
    assert ki.loc[0, "hazai"] == "Brentford"
    assert ki.loc[0, "hazai_gol"] == 2


def test_normalizal_zaro_odds_a_pinnacletol() -> None:
    """Alapesetben a Pinnacle (PS/P) záró ára kerül be, nem a tartalék."""
    ki = tortenelmi._normalizal(_nyers(), "E0")
    assert ki.loc[0, "zaro_1x2_h"] == pytest.approx(2.50)
    assert ki.loc[0, "zaro_1x2_d"] == pytest.approx(3.40)
    assert ki.loc[0, "zaro_1x2_a"] == pytest.approx(2.90)
    assert ki.loc[0, "zaro_ou25_tobb"] == pytest.approx(1.90)
    assert ki.loc[0, "zaro_ou25_kevesebb"] == pytest.approx(1.95)


def test_normalizal_hianyzo_pinnacle_eseten_tartalek() -> None:
    """Ha a Pinnacle ára hiányzik, a B365-re esünk vissza — soronként."""
    ki = tortenelmi._normalizal(_nyers(PSCH=[None, 1.80], **{"PC>2.5": [None, 2.05]}), "E0")
    assert ki.loc[0, "zaro_1x2_h"] == pytest.approx(2.45)  # tartalék
    assert ki.loc[1, "zaro_1x2_h"] == pytest.approx(1.80)  # eredeti megmarad
    assert ki.loc[0, "zaro_ou25_tobb"] == pytest.approx(1.88)


def test_normalizal_hianyzo_oszlop_nem_dob_hibat() -> None:
    """Régebbi szezonokban egy-egy odds-oszlop teljesen hiányozhat."""
    nyers = _nyers().drop(columns=["PSCH"])
    ki = tortenelmi._normalizal(nyers, "E0")
    assert ki.loc[0, "zaro_1x2_h"] == pytest.approx(2.45)


def test_normalizal_eldobja_a_le_nem_jatszott_meccset() -> None:
    """Eredmény nélküli sor sem illesztésre, sem backtesztre nem használható."""
    ki = tortenelmi._normalizal(_nyers(FTHG=[2, None]), "E0")
    assert len(ki) == 1
    assert ki.loc[0, "hazai"] == "Brentford"


def test_normalizal_datum_szerint_rendez() -> None:
    ki = tortenelmi._normalizal(_nyers(date=["2024-08-20", "2024-08-10"]), "E0")
    assert ki["datum"].is_monotonic_increasing
    assert ki.loc[0, "hazai"] == "Arsenal"


# ---------------------------------------------------------------------------
# Hibakezelés
# ---------------------------------------------------------------------------


def test_ismeretlen_liga_hibat_dob() -> None:
    with pytest.raises(AdatgyujtesHiba, match="Ismeretlen liga"):
        tortenelmi.footballdata_letoltes("NINCS_ILYEN", ["2425"])


def test_soccerdata_nev_nelkuli_liga_hibat_dob() -> None:
    """A Championshipnek nincs `soccerdata_liga`-ja — nem találgatunk."""
    with pytest.raises(AdatgyujtesHiba, match="soccerdata_liga"):
        tortenelmi.footballdata_letoltes("E1", ["2425"])
