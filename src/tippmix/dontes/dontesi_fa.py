"""8. lépés — Döntési fa: mi lesz tippből javaslat.

Minden jelölt (egy esemény + egy piac + egy kimenetel) végigmegy ezen a soron.
AZ ELSŐ BUKOTT FELTÉTELNÉL KIESIK, és a kiesés okát a program naplózza.
Csak a végigment jelöltekből lesz javaslat.

     1. Van érvényes szorzó?                    nem → NINCS_ODDS
     2. min_odds <= odds <= max_odds?           nem → ODDS_TARTOMANY
     3. Kezdésig >= 45 perc?                    nem → KESO
     4. Névillesztés megvan?                    nem → NEVILLESZTES_HIANY
     5. Elég adat mindkét csapatra (>= 12)?     nem → KEVES_ADAT
     6. A ligamodell friss (<= 8 nap)?          nem → MODELL_ELAVULT
     7. A piac támogatott ehhez a sporthoz?     nem → NEM_TAMOGATOTT_PIAC
     8. edge >= min_edge (napszak szerint)?     nem → KIS_EL
     9. EV >= min_ev?                           nem → KIS_EV
    10. Eltérés a referenciától < 8 pp?         nem → REFERENCIA_ELTERES
    11. HÍRVÉTÓ: van kizáró hír?                igen → HIRVETO
    12. Ment már ma javaslat erre az eseményre? igen → DUPLIKATUM
     → TÚLÉLT: megy a 9. lépésbe (tétezés)

AMIT A FA SZÁNDÉKOSAN NEM TARTALMAZ:
  - Nincs "biztos tipp" kategória. Nincs olyan feltétel, ami valamit
    felülírna és átengedne a szűrőkön.
  - Nincs sorozat-alapú logika ("a csapat 5 meccse veretlen, tehát…").
    Ez a modell dolga, nem külön szabályé.
  - NINCS VESZTESÉGPÓTLÁS. Ha az előző nap mínusz volt, az a mai tétekre
    semmilyen hatással nincs. Ez a legfontosabb védelem a bankroll ellen.

VÁZ: a függvények szignatúrája végleges, a törzs még nincs megírva.
"""

from __future__ import annotations

from datetime import datetime

from tippmix.kozos.naplo import naplo
from tippmix.kozos.tipusok import Jelolt, Kieses

log = naplo(__name__)


def ertekel(
    jelolt: Jelolt,
    futas_tipusa: str,
    most: datetime,
    mar_javasolt_esemenyek: set[str],
) -> Kieses | None:
    """Egy jelölt végigfuttatása a döntési fán.

    Args:
        futas_tipusa: "delelott" | "este" — ez választja a min_edge küszöböt
        mar_javasolt_esemenyek: a mai nap már javasolt tippmix_event_id-jei
            (a 12. pont, DUPLIKATUM)

    Returns:
        None, ha a jelölt TÚLÉLT (megy a tétezésbe).
        Kieses, ha valamelyik feltételen elbukott.
    """
    raise NotImplementedError("8. lépés — a Fázis 4-ben készül el")


def szur(
    jeloltek: list[Jelolt],
    futas_tipusa: str,
    most: datetime,
    mar_javasolt_esemenyek: set[str],
) -> tuple[list[Jelolt], list[Kieses]]:
    """A teljes jelöltlista végigfuttatása a döntési fán.

    Returns:
        (túlélők, kiesések)
    """
    raise NotImplementedError("8. lépés — a Fázis 4-ben készül el")
