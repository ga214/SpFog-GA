"""9. lépés — Tétezés Kelly-formulával.

"Nem fix tét, mert egy 1,4-es eseményre többet teszek, mint egy 10-esre."
Pontosan ezt csinálja a Kelly-formula, matematikailag megalapozottan.

    f* = (p × odds - 1) / (odds - 1)

Ugyanaz az 5%-os él, két különböző szorzónál (50 000 Ft bankroll,
negyed-Kelly, 4% plafon):

    | Szorzó | p_végleges |   f*   | negyed-Kelly | tét            |
    |  1,40  |   0,764    | 0,174  |    0,0435    | 2 175 → 2 000  | (a 4% plafon vág)
    |  3,50  |   0,331    | 0,064  |    0,0160    |   800 Ft       |
    |  6,00  |   0,197    | 0,036  |    0,0091    |   455 →   500  |

A teljes tétszámítás lépései (spec 9. lépés):
  1. f* = (p_végleges × odds − 1) / (odds − 1)
  2. Ha f* <= 0 → nincs tipp
  3. f_használt = f* × kelly_hányad (0,25)
  4. tét = f_használt × bankroll_aktuális
  5. Levágás felülről: min(tét, max_ft, max_bankroll_százalék × bankroll)
  6. Levágás alulról: ha tét < min_ft (200) → KIESIK TUL_KIS_TET okkal.
     NEM kerekítünk fel, mert az felültetéléshez vezet.
  7. Kerekítés 100 Ft-ra LEFELÉ.

MIÉRT NEGYED-KELLY? A teljes Kelly akkor optimális, ha a p becslésed PONTOS.
A miénk nem az — becslés, hibával. Ha a valós p alacsonyabb, mint hitted, a
teljes Kelly gyorsan tönkretesz. A negyed-Kelly a várható növekedés kb.
75%-át hozza a volatilitás negyedéért.
"""

from __future__ import annotations

import math

from tippmix.kozos.naplo import naplo

log = naplo(__name__)


def kelly_nyers(p: float, odds: float) -> float:
    """Az optimális bankroll-hányad: f* = (p × odds - 1) / (odds - 1).

    Args:
        p: a végleges valószínűség [0, 1]
        odds: decimális szorzó (> 1)

    Returns:
        f*. Negatív vagy nulla, ha nincs él — ilyenkor nem szabad fogadni.

    Raises:
        ValueError: érvénytelen bemenet
    """
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"p kívül esik a [0,1] tartományon: {p}")
    if odds <= 1.0:
        raise ValueError(f"Érvénytelen szorzó: {odds} (1-nél nagyobbnak kell lennie)")
    return (p * odds - 1.0) / (odds - 1.0)


def tet_szamitas(
    p: float,
    odds: float,
    bankroll_ft: int,
    kelly_hanyad: float,
    min_ft: int,
    max_ft: int,
    max_bankroll_szazalek: float,
    kerekites_ft: int,
) -> tuple[int, float, float]:
    """A teljes tétszámítás a spec 9. lépése szerint.

    Returns:
        (tét_ft, f*, f_használt)
        A tét 0, ha a tipp kiesik TUL_KIS_TET okkal — ezt a hívó kezeli.

    Raises:
        ValueError: érvénytelen bemenet
    """
    if bankroll_ft <= 0:
        raise ValueError(f"Érvénytelen bankroll: {bankroll_ft}")
    if kerekites_ft <= 0:
        raise ValueError(f"Érvénytelen kerekítés: {kerekites_ft}")

    # 1. lépés
    f_csillag = kelly_nyers(p, odds)

    # 2. lépés: ide elvileg nem juthatunk el, mert a 8. lépés kiszűrte
    if f_csillag <= 0.0:
        return 0, f_csillag, 0.0

    # 3. lépés
    f_hasznalt = f_csillag * kelly_hanyad

    # 4. lépés
    tet = f_hasznalt * bankroll_ft

    # 5. lépés: levágás felülről — a max_ft és a bankroll-százalék közül a
    # szigorúbb nyer. 50 000 Ft-nál a 4% = 2 000 Ft, tehát ez a plafon,
    # nem az 5 000 Ft.
    plafon = min(float(max_ft), max_bankroll_szazalek * bankroll_ft)
    tet = min(tet, plafon)

    # 6. lépés: levágás alulról. NEM kerekítünk fel.
    if tet < min_ft:
        return 0, f_csillag, f_hasznalt

    # 7. lépés: kerekítés LEFELÉ
    tet_kerekitve = int(math.floor(tet / kerekites_ft) * kerekites_ft)

    # A lefelé kerekítés a min_ft alá vihet (pl. 250 → 200 rendben, de ha a
    # min_ft 250 lenne, a 299 → 200 már nem). Újraellenőrizzük.
    if tet_kerekitve < min_ft:
        return 0, f_csillag, f_hasznalt

    return tet_kerekitve, f_csillag, f_hasznalt


def lehetseges_nyeremeny(tet_ft: int, odds: float) -> int:
    """A teljes kifizetés nyerés esetén (a tétet is beleértve), lefelé kerekítve."""
    return math.floor(tet_ft * odds)


def napi_limit_alkalmazas(
    tetek_ft: list[int],
    max_kitettseg_ft: int,
    min_ft: int,
    kerekites_ft: int,
) -> list[int]:
    """11. lépés / 3. pont: arányos csökkentés, ha a napi kitettség túl nagy.

    "Ha az összeg > max_kitettség, akkor arányosan csökkentsd az összes
    tétet, amíg belefér. Ha valamelyik így 200 Ft alá esik, azt hagyd ki, és
    számold újra."

    Returns:
        A módosított tétek, ugyanabban a sorrendben. A kihagyott tételek
        helyén 0 áll.
    """
    if not tetek_ft:
        return []

    aktualis = list(tetek_ft)

    # Legfeljebb annyiszor iterálunk, ahány tétel van: minden körben
    # legalább egy kiesik, különben kilépünk.
    for _ in range(len(tetek_ft) + 1):
        osszeg = sum(aktualis)
        if osszeg <= max_kitettseg_ft or osszeg == 0:
            return aktualis

        arany = max_kitettseg_ft / osszeg
        csokkentett = [
            int(math.floor(t * arany / kerekites_ft) * kerekites_ft) if t > 0 else 0
            for t in aktualis
        ]

        # Ami a min_ft alá esett, azt kihagyjuk, és újraszámolunk
        kiesett = [i for i, t in enumerate(csokkentett) if 0 < t < min_ft]
        if not kiesett:
            return csokkentett

        for i in kiesett:
            aktualis[i] = 0

    log.warning("napi_limit_nem_konvergalt", tetek=tetek_ft, limit=max_kitettseg_ft)
    return [0] * len(tetek_ft)
