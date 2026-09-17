"""10. lépés — Kombináció-építés.

A SZABÁLY EGY MONDATBAN: kombináció csak olyan lábakból épülhet, amelyek
KÜLÖN-KÜLÖN IS ÁTMENTEK A 8. LÉPÉS TELJES DÖNTÉSI FÁJÁN. A kombináció nem
eszköz a szorzó feltornázására.

Az építés menete (spec 10. lépés):
  1. Vedd a túlélt egyes tippeket.
  2. Csak az edge >= min_láb_edge (5 pp) feletti lábak. Szigorúbb, mint az
     egyesnél.
  3. Zárd ki az azonos eseményhez tartozókat (korreláció + kötéstiltás).
  4. Lehetőleg különböző bajnokságból (közvetett korreláció).
  5. Minden 2-es és 3-as kombináció:
         kombi_odds = Π odds_i
         kombi_p    = Π p_végleges_i
         kombi_EV   = kombi_p × kombi_odds - 1
  6. Tartsd meg, ahol kombi_EV >= min_ev (3%).
  7. Rendezd kombi_EV szerint, vedd a legjobb max_kombináció_db (2) darabot.
  8. Tét: a Kelly-érték FELE (tét_szorzó 0.5) — a lábak közti rejtett
     korreláció és a halmozott modellhiba miatt.
  9. Ellenőrizd: tét × kombi_odds <= 2 000 000 Ft (Tippmix nyereményplafon).

A MATEK, AMIT TUDNI KELL: tíz darab 1,05-ös esemény összefűzve kb. 5% biztos
veszteség, miközben a szelvény csak 0,95^10 ≈ 60%-ban jön be egyáltalán.
Ezért max_láb: 3, és ezért csak +EV lábakból.

MIKOR VAN ÉRTELME? Ha minden láb önmagában +5% EV-t hoz, egy 2-es kombináció
elméleti EV-je 1,05 × 1,05 − 1 = 10,25% — a pozitív él is halmozódik. Ez az
EGYETLEN eset, amikor a kombináció jobb az egyesnél.

VÁZ: a függvények szignatúrája végleges, a törzs még nincs megírva.
"""

from __future__ import annotations

from tippmix.kozos.naplo import naplo
from tippmix.kozos.tipusok import Javaslat, Kombinacio

log = naplo(__name__)


def epit(javaslatok: list[Javaslat]) -> list[Kombinacio]:
    """Kombinációk építése a túlélt egyes tippekből.

    Returns:
        Legfeljebb max_kombináció_db darab, kombi_EV szerint csökkenően.
    """
    raise NotImplementedError("10. lépés — a Fázis 5-ben készül el")


def kombinalhato(a: Javaslat, b: Javaslat) -> bool:
    """Összefűzhető-e két láb.

    Nem, ha:
      - ugyanahhoz az eseményhez tartoznak (korreláció + kötéstiltás)
      - bármelyikre kötéstiltás van érvényben
    """
    raise NotImplementedError("10. lépés — a Fázis 5-ben készül el")


def nyeremenyplafon_ellenorzes(tet_ft: int, kombi_odds: float, plafon_ft: int) -> int:
    """A tét levágása, hogy a nyeremény ne lépje túl a platform plafonját.

    Kis téteknél ez sosem fog fogni, de a kód tartalmazza.

    Returns:
        A módosított tét.
    """
    raise NotImplementedError("10. lépés — a Fázis 5-ben készül el")
