"""7. lépés — Vig eltávolítása és az él kiszámítása.

A VIG (árrés) az, amit az iroda beépít a szorzóba. Egy 1X2 piacon a három
szorzó reciprokainak összege nem 1, hanem pl. 1,06. Ez a 6% az iroda haszna.

HA EZT NEM VESSZÜK KI, MINDEN ÉLÜNK HAMIS LESZ — 6%-kal jobbnak fogjuk hinni
magunkat, mint amilyenek vagyunk.

A számítás (spec 7. lépés):
  1. Nyers implikált valószínűség: q_i = 1 / odds_i
  2. Az összegük: S = Σ q_i (ez > 1)
  3. Power módszer: keressük azt a k kitevőt, amire Σ (q_i)^k = 1.
     Bisection-nel megoldva. A fair valószínűség: p_fair_i = (q_i)^k

MIÉRT POWER ÉS NEM EGYSZERŰ OSZTÁS? Az egyszerű arányos osztás (q_i / S)
minden kimenetelből ugyanannyi százalékot vesz ki. A valóságban az irodák a
kis esélyű kimenetelekre tesznek arányosan nagyobb árrést
(favourite-longshot bias). A power módszer ezt figyelembe veszi.

Az arányos változatot REFERENCIAKÉNT végigszámoljuk, és ha a kettő nagyon
eltér, az figyelmeztető jel.
"""

from __future__ import annotations

from dataclasses import dataclass

from tippmix.kozos.naplo import naplo

log = naplo(__name__)

# A bisection numerikus paraméterei
_BISECTION_TOLERANCIA = 1e-10
_BISECTION_MAX_LEPES = 200
_K_ALSO = 0.01
_K_FELSO = 10.0


# Egy valós piac overroundja ezek között mozog. Ezen kívül esni gyanús.
_OVERROUND_MIN = 0.0
_OVERROUND_MAX = 0.25

# Ha a power és az arányos módszer ennél jobban eltér, az figyelmeztető jel.
_MAX_MODSZER_ELTERES = 0.05


@dataclass(frozen=True, slots=True)
class VigEredmeny:
    """Egy piac vig-mentesített valószínűségei."""

    p_fair: tuple[float, ...]  # power módszer — ezt használjuk
    p_fair_aranyos: tuple[float, ...]  # proportional — referencia
    overround: float  # S - 1, az iroda árrése
    k_kitevo: float  # a megtalált power-kitevő
    max_elteres: float  # a két módszer legnagyobb eltérése
    gyanus: bool = False  # az eredmény nem megbízható
    gyanu_oka: str = ""


def implikalt(odds: float) -> float:
    """Nyers implikált valószínűség: q = 1 / odds."""
    if odds <= 1.0:
        raise ValueError(f"Érvénytelen szorzó: {odds} (1-nél nagyobbnak kell lennie)")
    return 1.0 / odds


def overround(oddsok: list[float]) -> float:
    """Az iroda árrése: S - 1, ahol S a reciprokok összege.

    1X2 piacon egy tipikus érték 0.05-0.08 (5-8%).
    """
    return sum(implikalt(o) for o in oddsok) - 1.0


def aranyos_eltavolitas(oddsok: list[float]) -> tuple[float, ...]:
    """Proportional (multiplicative) vig-eltávolítás: p_i = q_i / S.

    Egyszerű, de nem kezeli a favourite-longshot bias-t. Referenciaként
    használjuk, nem döntéshez.
    """
    q = [implikalt(o) for o in oddsok]
    s = sum(q)
    return tuple(qi / s for qi in q)


def power_eltavolitas(oddsok: list[float]) -> tuple[tuple[float, ...], float]:
    """Power vig-eltávolítás: keressük a k kitevőt, amire Σ (q_i)^k = 1.

    Bisection-nel. A k mindig 1-nél nagyobb lesz (mert Σ q_i > 1, és a
    q_i értékek 1-nél kisebbek, így nagyobb kitevő csökkenti az összeget).

    Returns:
        (fair valószínűségek, a megtalált k)

    Raises:
        ValueError: a bisection nem talált megoldást a keresési tartományban
    """
    q = [implikalt(o) for o in oddsok]

    def osszeg(k: float) -> float:
        return sum(qi**k for qi in q)

    also, felso = _K_ALSO, _K_FELSO

    # Az osszeg(k) szigorúan monoton csökkenő k-ban (mert minden q_i < 1).
    # Ellenőrizzük, hogy a gyök a tartományon belül van-e.
    if osszeg(also) < 1.0 or osszeg(felso) > 1.0:
        raise ValueError(
            f"A power-kitevő nincs a [{_K_ALSO}, {_K_FELSO}] tartományban. "
            f"Szorzók: {oddsok}, Σq = {sum(q):.4f}"
        )

    for _ in range(_BISECTION_MAX_LEPES):
        kozep = (also + felso) / 2.0
        ertek = osszeg(kozep)
        if abs(ertek - 1.0) < _BISECTION_TOLERANCIA:
            break
        if ertek > 1.0:
            also = kozep
        else:
            felso = kozep
    else:
        log.warning("bisection_nem_konvergalt", oddsok=oddsok, k=kozep, osszeg=ertek)

    k = (also + felso) / 2.0
    return tuple(qi**k for qi in q), k


def vig_eltavolitas(oddsok: list[float]) -> VigEredmeny:
    """Egy piac teljes vig-eltávolítása, mindkét módszerrel.

    Args:
        oddsok: EGY piac ÖSSZES kimenetelének szorzója. 1X2-nél három elem,
            over/under-nél kettő. Hiányos lista hamis eredményt ad, mert az
            overround rosszul számolódik.

    Raises:
        ValueError: kevesebb mint 2 kimenetel, vagy érvénytelen szorzó
    """
    if len(oddsok) < 2:
        raise ValueError(
            f"Legalább 2 kimenetel kell a vig-eltávolításhoz, kapott: {len(oddsok)}. "
            "Egy piac ÖSSZES kimenetelét át kell adni."
        )

    p_power, k = power_eltavolitas(oddsok)
    p_aranyos = aranyos_eltavolitas(oddsok)
    max_elt = max(abs(a - b) for a, b in zip(p_power, p_aranyos, strict=True))
    o = sum(implikalt(x) for x in oddsok) - 1.0

    # Gyanú-ellenőrzés: egy valós fogadóiroda soha nem ad negatív overroundot.
    # Ha mégis ilyet látunk, az vagy hiányos kimenetel-lista (a piac egy
    # részét adtuk át), vagy elrontott scraping. Csendben átengedni veszélyes:
    # hamis élt gyártana.
    okok: list[str] = []
    if o < _OVERROUND_MIN:
        okok.append(f"negatív overround ({o:.4f}) — hiányos kimenetel-lista vagy hibás adat")
    elif o > _OVERROUND_MAX:
        okok.append(f"szokatlanul magas overround ({o:.4f})")

    if max_elt > _MAX_MODSZER_ELTERES:
        okok.append(f"a power és az arányos módszer nagyon eltér ({max_elt:.4f})")

    if okok:
        log.warning("gyanus_piac", oddsok=oddsok, overround=round(o, 4), okok=okok)

    return VigEredmeny(
        p_fair=p_power,
        p_fair_aranyos=p_aranyos,
        overround=o,
        k_kitevo=k,
        max_elteres=max_elt,
        gyanus=bool(okok),
        gyanu_oka="; ".join(okok),
    )


# =============================================================================
# Él és várható hozam
# =============================================================================


def edge(p_vegleges: float, p_fair: float) -> float:
    """Az él százalékpontban: mennyivel gondoljuk valószínűbbnek a piacnál.

    edge = p_végleges - p_fair
    """
    return p_vegleges - p_fair


def ev(p_vegleges: float, odds: float) -> float:
    """A várható hozam arányosan.

        EV = p_végleges × odds - 1

    Példa: p = 0.48, odds = 2.20 → EV = 0.056 (5.6% várható hozam)
    """
    if odds <= 1.0:
        raise ValueError(f"Érvénytelen szorzó: {odds}")
    return p_vegleges * odds - 1.0


def referencia_elteres(p_vegleges: float, referencia_p_fair: float) -> float:
    """Eltérés a nemzetközi konszenzustól, abszolút értékben.

    Ha ez több mint max_eltérés_referenciától (8 pp), az azt jelenti, hogy a
    modellünk valamit nem tud, amit a piac tud → REFERENCIA_ELTERES kiesés.
    Ez a védőháló a sérülés- és hírhiányból fakadó vak élek ellen.
    """
    return abs(p_vegleges - referencia_p_fair)
