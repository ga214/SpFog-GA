"""1. lépés — az esemény-begyűjtés tesztjei.

Hálózat NÉLKÜL: a Tippmix válaszának szerkezetét rögzített minták képviselik,
a 2026-09-18-i felderítésből (docs/OPEN_QUESTIONS.md NY-11).

Amit ezek a tesztek védenek, az a két csendes hiba, amit az első éles próba
felszínre hozott:
  1. a részstring-egyezés rossz bajnokságokat engedett be, a jót meg kihagyta,
  2. az 1X2 kimenetel neve a csapat neve volt, nem a pozíció.
Mindkettő úgy hibázott, hogy nem dobott kivételt — csak rossz adatot adott.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tippmix.gyujtes import tippmix_scraper as scraper
from tippmix.gyujtes.wamp_kliens import rekordok_tipus_szerint

KIMENETEL_KOD = {
    "home": "1",
    "draw": "X",
    "away": "2",
    "over": "Tobb",
    "under": "Kevesebb",
}

MECCS = {
    "_type": "MATCH",
    "id": "313617673133649920",
    "name": "Brentford - Chelsea",
    "homeParticipantName": "Brentford",
    "awayParticipantName": "Chelsea",
    "startTime": 1789758000000,
}


def _odds_rekordok() -> list[dict]:
    """Egy 1X2 piac három kimenetellel, a Tippmix rekordszerkezetében."""
    return [
        {"_type": "MARKET", "id": "M1", "name": "1X2 - Rendes játékidő", "mainLine": True},
        {"_type": "OUTCOME", "id": "O_H", "headerNameKey": "home", "translatedName": "Brentford"},
        {"_type": "OUTCOME", "id": "O_D", "headerNameKey": "draw", "translatedName": "Döntetlen"},
        {"_type": "OUTCOME", "id": "O_A", "headerNameKey": "away", "translatedName": "Chelsea"},
        {"_type": "MARKET_OUTCOME_RELATION", "marketId": "M1", "outcomeId": "O_H"},
        {"_type": "MARKET_OUTCOME_RELATION", "marketId": "M1", "outcomeId": "O_D"},
        {"_type": "MARKET_OUTCOME_RELATION", "marketId": "M1", "outcomeId": "O_A"},
        {"_type": "BETTING_OFFER", "outcomeId": "O_H", "odds": 2.69, "isAvailable": True},
        {"_type": "BETTING_OFFER", "outcomeId": "O_D", "odds": 3.95, "isAvailable": True},
        {"_type": "BETTING_OFFER", "outcomeId": "O_A", "odds": 2.46, "isAvailable": True},
    ]


def _epit(rekordok: list[dict] | None = None):
    return scraper._esemenyekke(
        MECCS,
        _odds_rekordok() if rekordok is None else rekordok,
        "foci",
        "Premier Liga",
        datetime(2026, 9, 18, 19, 0, tzinfo=UTC),
        KIMENETEL_KOD,
    )


# ---------------------------------------------------------------------------
# Rekordcsoportosítás
# ---------------------------------------------------------------------------


def test_rekordok_tipus_szerint_csoportosit() -> None:
    csoportok = rekordok_tipus_szerint(_odds_rekordok())
    assert len(csoportok["OUTCOME"]) == 3
    assert len(csoportok["BETTING_OFFER"]) == 3
    assert len(csoportok["MARKET"]) == 1


# ---------------------------------------------------------------------------
# Bajnokság-párosítás — a részstring-hiba elleni védelem
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tippmix_nev", "vart"),
    [
        ("Premier Liga 2026/2027", "Premier Liga"),
        ("NBA 2026/2027", "NBA"),
        ("Indiai Mizoram Premier Liga 2026", "Indiai Mizoram Premier Liga"),
        ("Bundesliga 1. 2026/2027", "Bundesliga 1."),
        ("Serie A", "Serie A"),
    ],
)
def test_evad_levagasa(tippmix_nev: str, vart: str) -> None:
    assert scraper._evad_nelkul(tippmix_nev) == vart


def test_bajnoksag_pontos_egyezes_kell() -> None:
    engedelyezett = {"Premier Liga", "Bundesliga 1."}
    assert scraper._bajnoksag_engedelyezett("Premier Liga 2026/2027", engedelyezett)
    assert scraper._bajnoksag_engedelyezett("Bundesliga 1. 2026/2027", engedelyezett)


def test_bajnoksag_nem_enged_be_hasonlot() -> None:
    """Ez a konkrét eset ment át a régi részstring-logikán, csendben."""
    engedelyezett = {"Premier Liga", "Bundesliga 1."}
    for hamis in (
        "Angol Isthmian Premier Liga 2026/2027",
        "Indiai Mizoram Premier Liga 2026",
        "Premier Liga 2., Divízió 1. 2026/2027",
        "Bundesliga 2. 2026/2027",
        "Bundesliga 3. 2026/2027",
    ):
        assert not scraper._bajnoksag_engedelyezett(hamis, engedelyezett), hamis


# ---------------------------------------------------------------------------
# Rekordokból NyersEsemeny — a kimenetelnév-hiba elleni védelem
# ---------------------------------------------------------------------------


def test_esemenyekke_normalizalt_kimeneteleket_ad() -> None:
    """A kimenetel a pozíció kódja legyen, NE a csapat neve."""
    sorok = _epit()
    assert {s.kimenetel_nev for s in sorok} == {"1", "X", "2"}
    assert all(s.hazai_nev == "Brentford" for s in sorok)


def test_esemenyekke_szorzot_parositja() -> None:
    szorzok = {s.kimenetel_nev: s.odds for s in _epit()}
    assert szorzok == {"1": 2.69, "X": 3.95, "2": 2.46}


def test_esemenyekke_kihagyja_a_nem_elerheto_ajanlatot() -> None:
    rekordok = [
        r
        for r in _odds_rekordok()
        if not (r["_type"] == "BETTING_OFFER" and r["outcomeId"] == "O_D")
    ]
    rekordok.append(
        {"_type": "BETTING_OFFER", "outcomeId": "O_D", "odds": 3.95, "isAvailable": False}
    )
    assert {s.kimenetel_nev for s in _epit(rekordok)} == {"1", "2"}


def test_esemenyekke_kihagyja_az_ismeretlen_kimenetelt() -> None:
    """Ismeretlen `headerNameKey` → kihagyás, nem találgatás."""
    rekordok = [r for r in _odds_rekordok() if r.get("id") != "O_D"]
    rekordok.append(
        {"_type": "OUTCOME", "id": "O_D", "headerNameKey": "valami_uj", "translatedName": "?"}
    )
    assert {s.kimenetel_nev for s in _epit(rekordok)} == {"1", "2"}


def test_esemenyekke_kihagyja_az_ervenytelen_szorzot() -> None:
    rekordok = [r for r in _odds_rekordok() if r.get("outcomeId") != "O_H"]
    rekordok.append({"_type": "MARKET_OUTCOME_RELATION", "marketId": "M1", "outcomeId": "O_H"})
    rekordok.append({"_type": "BETTING_OFFER", "outcomeId": "O_H", "odds": 1.0})
    assert {s.kimenetel_nev for s in _epit(rekordok)} == {"X", "2"}


def test_esemenyekke_nev_nelkuli_meccset_kihagy() -> None:
    meccs = {k: v for k, v in MECCS.items() if k != "homeParticipantName"}
    assert (
        scraper._esemenyekke(
            meccs,
            _odds_rekordok(),
            "foci",
            "Premier Liga",
            datetime(2026, 9, 18, 19, 0, tzinfo=UTC),
            KIMENETEL_KOD,
        )
        == []
    )


def test_kezdes_utc_epoch_ezredmasodpercbol() -> None:
    kezdes = scraper._kezdes_utc(MECCS)
    assert kezdes == datetime(2026, 9, 18, 19, 0, tzinfo=UTC)


def test_kezdes_utc_hianyzo_mezonel_none() -> None:
    assert scraper._kezdes_utc({"id": "x"}) is None
