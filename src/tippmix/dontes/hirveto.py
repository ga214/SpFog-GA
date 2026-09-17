"""8. lépés / 11. pont — Hírvétó.

A HÍRRÉTEG SOHA NEM HOZ LÉTRE TIPPET, CSAK MEGÖL.

Ez szándékos: a hírek számszerűsítése megbízhatatlan, de arra jó, hogy egy
nyilvánvalóan elavult modellbecslést leállítson.

Vétófeltételek (spec 8. lépés táblázata):

    Kosár  — kulcsjátékos OUT vagy DOUBTFUL a hivatalos NBA Injury Reportban
    Kosár  — a csapat top-2 percátlagú játékosa hiányzik
    Foci   — megerősített kezdő tizenegyben hiányzik a 2 legtöbbet játszó
             mezőnyjátékos vagy a kezdő kapus
    Foci   — a felállás még nem elérhető ÉS a délelőtti futásban vagyunk
             → ekkor min_edge_délelőtt a magasabb küszöb, NEM vétó
    Mindkettő — a meccs státusza nem "scheduled" (halasztva, törölve)

FONTOS KORLÁT: a "kulcsjátékos" definíciója az elmúlt N meccs
játékperceiből származik, NEM szubjektív megítélésből.

HA A HÍRFORRÁS NEM ELÉRHETŐ: a program NEM vétóz vakon — ehelyett a napszaki
küszöböt megemeli 1,5-szeresére, és a levélben jelzi, hogy nem volt
hírellenőrzés.

VÁZ: a függvények szignatúrája végleges, a törzs még nincs megírva.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from tippmix.kozos.naplo import naplo
from tippmix.kozos.tipusok import Esemeny

log = naplo(__name__)


class HirAllapot(StrEnum):
    TISZTA = "tiszta"  # ellenőriztük, nincs kizáró hír
    VETO = "veto"  # ellenőriztük, van kizáró hír
    NINCS_ELLENORZES = "nincs_ellenorzes"  # a forrás nem volt elérhető


@dataclass(frozen=True, slots=True)
class HirEredmeny:
    allapot: HirAllapot
    indok: str = ""
    # Ha NINCS_ELLENORZES, a küszöböt ennyiszeresére kell emelni
    kuszob_szorzo: float = 1.0


def ellenoriz(esemeny: Esemeny, futas_tipusa: str) -> HirEredmeny:
    """Hírvétó-ellenőrzés egy eseményre."""
    raise NotImplementedError("8. lépés / hírvétó — a Fázis 5-ben készül el")


def nba_injury_report() -> dict[str, list[str]]:
    """A hivatalos NBA Injury Report letöltése és feldolgozása (PDF).

    Returns:
        {csapat_id: [hiányzó játékosok]}
    """
    raise NotImplementedError("8. lépés / hírvétó — a Fázis 7-ben készül el")


def foci_felallas(esemeny: Esemeny) -> list[str] | None:
    """A megerősített kezdő tizenegy, ha már elérhető.

    A felállások jellemzően a kezdés előtt ~1 órával jelennek meg.

    Returns:
        None, ha még nem elérhető.
    """
    raise NotImplementedError("8. lépés / hírvétó — a Fázis 5-ben készül el")


def kulcsjatekosok(csapat_id: str, sport: str, ablak_meccs: int, top_k: int) -> list[str]:
    """A csapat kulcsjátékosai az elmúlt N meccs játékpercei alapján.

    NEM szubjektív megítélés — az adat dönt.
    """
    raise NotImplementedError("8. lépés / hírvétó — a Fázis 5-ben készül el")
