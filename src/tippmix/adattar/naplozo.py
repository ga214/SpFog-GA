"""12. lépés — Naplózás és CLV.

A program naplója: minden javaslatról egy sor a Supabase `tippek` táblájába.
Enélkül a rendszer nem tud tanulni és nem tudod megmondani, működik-e.

VÁZ: a függvények szignatúrája végleges, a törzs még nincs megírva.
"""

from __future__ import annotations

from typing import Any

from tippmix.kozos.naplo import naplo
from tippmix.kozos.tipusok import FutasEredmeny

log = naplo(__name__)


def futas_rogzites(eredmeny: FutasEredmeny, allapot: str, futasido_mp: float) -> None:
    """A futás fejsorát írja a `futasok` táblába.

    Args:
        allapot: "sikeres" | "sikertelen" | "nincs_tipp"
    """
    raise NotImplementedError("12. lépés — a Fázis 5-ben készül el")


def javaslatok_rogzitese(eredmeny: FutasEredmeny) -> None:
    """A javaslatokat írja a `tippek` táblába, a kombinációkat a `kombinaciok`-ba."""
    raise NotImplementedError("12. lépés — a Fázis 5-ben készül el")


def kiesesek_rogzitese(eredmeny: FutasEredmeny) -> None:
    """A kiesési okokat összesítve írja a `kiesesek` táblába."""
    raise NotImplementedError("12. lépés — a Fázis 5-ben készül el")


def zaro_odds_frissites(tippmix_event_id: str, piac: str, kimenetel: str, zaro: float) -> None:
    """A záró szorzót írja be és számolja a CLV-t.

    CLV = (odds_javaslatkor / zaro_odds) - 1
    """
    raise NotImplementedError("12. lépés — a Fázis 5-ben készül el")


def leallitasi_feltetel_ellenorzes() -> tuple[bool, str]:
    """Teljesült-e valamelyik automatikus leállítási feltétel.

    Returns:
        (leall, indoklas)
    """
    raise NotImplementedError("12. lépés — a Fázis 5-ben készül el")


def clv_osszesites() -> dict[str, Any]:
    """A `v_clv_osszesites` nézet lekérdezése."""
    raise NotImplementedError("12. lépés — a Fázis 5-ben készül el")
