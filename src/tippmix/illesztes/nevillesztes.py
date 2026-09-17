"""2. lépés — Névillesztés.

EZ A RENDSZER LEGGYAKORIBB HIBAFORRÁSA.

A probléma: a Tippmix "Manchester Utd"-ot ír, a football-data.co.uk
"Man United"-ot, az Understat "Manchester United"-ot. Ha a program rosszul
köti össze, rossz csapat statisztikájából számol, és a javaslat értéktelen
— RÁADÁSUL ÉSZREVÉTLENÜL, mert semmi nem fog hibát dobni.

A megoldás: kézi leképezési tábla (data/team_aliases.csv), automatikus
javaslattal.

  1. Név szerepel a táblában → kész.
  2. Nem szerepel → fuzzy javaslat, de NEM használjuk fel automatikusan.
     Az esemény kimarad, a levél végén szerepel a javasolt párosítással.
     Te egy sorral kiegészíted a CSV-t, és másnaptól működik.

Miért nem automatikus? A fuzzy találat 95%-ban jó, 5%-ban csendben rossz
csapatot választ ("Manchester City" ↔ "Manchester Utd" hasonlósága magas).
Az 5% hibás párosítás rosszabb, mint az, hogy egy meccs kimarad.

VÁZ: a függvények szignatúrája végleges, a törzs még nincs megírva.
"""

from __future__ import annotations

from dataclasses import dataclass

from tippmix.kozos.naplo import naplo
from tippmix.kozos.tipusok import Esemeny, NyersEsemeny

log = naplo(__name__)


@dataclass(frozen=True, slots=True)
class IsmeretlenCsapat:
    """Egy nem illesztett név, fuzzy javaslattal."""

    tippmix_nev: str
    sport: str
    javasolt_kanonikus_id: str | None
    fuzzy_pontszam: int


def normalizal(nev: str) -> str:
    """Csapatnév normalizálása az összehasonlításhoz.

    Ékezetek le, kisbetűsítés, a gyakori toldalékok ("FC", "SK", "AC",
    "United", "Utd") egységesítése.
    """
    raise NotImplementedError("2. lépés — a Fázis 4-ben készül el")


def alias_tabla_betoltes() -> dict[tuple[str, str], str]:
    """A data/team_aliases.csv betöltése.

    Returns:
        {(normalizált_név, sport): kanonikus_id}
    """
    raise NotImplementedError("2. lépés — a Fázis 4-ben készül el")


def liga_tabla_betoltes() -> dict[tuple[str, str], str]:
    """A data/league_map.csv betöltése.

    Returns:
        {(tippmix_bajnokság, sport): liga_kod}
    """
    raise NotImplementedError("2. lépés — a Fázis 4-ben készül el")


def illeszt(
    nyers: list[NyersEsemeny],
) -> tuple[list[Esemeny], list[IsmeretlenCsapat]]:
    """Névillesztés: minden eseményhez kanonikus azonosítók.

    Returns:
        (illesztett események, ismeretlen csapatok fuzzy javaslattal)
    """
    raise NotImplementedError("2. lépés — a Fázis 4-ben készül el")


def fuzzy_javaslat(nev: str, sport: str, min_pontszam: int) -> tuple[str | None, int]:
    """Fuzzy javaslat egy ismeretlen névre. SOHA nem használjuk fel automatikusan.

    Returns:
        (javasolt_kanonikus_id vagy None, pontszám 0-100)
    """
    raise NotImplementedError("2. lépés — a Fázis 4-ben készül el")
