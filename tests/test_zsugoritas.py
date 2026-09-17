"""6. lépés — piaci zsugorítás tesztjei.

"Ez a legfontosabb pont az egész dokumentumban."
"""

from __future__ import annotations

import numpy as np
import pytest

from tippmix.modellek import kalibracio


def test_w_nulla_teljesen_a_piacot_koveti() -> None:
    """w = 0 → sosem lesz tipp, mert p_végleges == p_fair, tehát edge = 0."""
    p = kalibracio.zsugorit(p_kalibralt=0.70, p_piac_fair=0.50, w=0.0)
    assert p == pytest.approx(0.50)


def test_w_egy_csak_a_modell_szamit() -> None:
    p = kalibracio.zsugorit(p_kalibralt=0.70, p_piac_fair=0.50, w=1.0)
    assert p == pytest.approx(0.70)


def test_w_035_a_harmadat_viszi_at() -> None:
    """A kiindulási érték: a modell a piactól való eltérés harmadát viszi át."""
    p = kalibracio.zsugorit(p_kalibralt=0.70, p_piac_fair=0.50, w=0.35)
    # 0.35*0.70 + 0.65*0.50 = 0.245 + 0.325 = 0.57
    assert p == pytest.approx(0.57)
    # Az eredeti 20 pp eltérésből 7 pp maradt
    assert p - 0.50 == pytest.approx(0.20 * 0.35)


def test_zsugoritas_mindig_a_ket_ertek_kozott_van() -> None:
    """A keverék soha nem lép ki a két bemenet által határolt sávból."""
    for w in [0.0, 0.1, 0.35, 0.5, 0.9, 1.0]:
        p = kalibracio.zsugorit(0.80, 0.40, w)
        assert 0.40 <= p <= 0.80


def test_zsugoritas_csokkenti_a_tippek_szamat() -> None:
    """A zsugorítás következménye: sokkal kevesebb tipp.

    Ha a modell 60%-ot mond ott, ahol a piac 50%-ot, a nyers él 10 pp.
    w=0.35 mellett ez 3,5 pp-re esik — a min_edge_délelőtt (5 pp) alá.
    """
    nyers_el = 0.60 - 0.50
    p_vegleges = kalibracio.zsugorit(0.60, 0.50, 0.35)
    zsugoritott_el = p_vegleges - 0.50

    assert nyers_el == pytest.approx(0.10)
    assert zsugoritott_el == pytest.approx(0.035)
    assert zsugoritott_el < 0.05  # a délelőtti küszöb alatt → nincs tipp


def test_zsugoritas_ervenytelen_bemenet() -> None:
    with pytest.raises(ValueError, match="p_kalibralt"):
        kalibracio.zsugorit(1.5, 0.5, 0.35)
    with pytest.raises(ValueError, match="p_piac_fair"):
        kalibracio.zsugorit(0.5, -0.1, 0.35)
    with pytest.raises(ValueError, match="w kívül esik"):
        kalibracio.zsugorit(0.5, 0.5, 1.5)


def test_brier_tokeletes_becsles() -> None:
    """Tökéletes becslés → 0 Brier-pontszám."""
    p = np.array([1.0, 0.0, 1.0, 0.0])
    y = np.array([1.0, 0.0, 1.0, 0.0])
    assert kalibracio.brier_pontszam(p, y) == pytest.approx(0.0)


def test_brier_legrosszabb_becsles() -> None:
    """Teljesen rossz becslés → 1.0."""
    p = np.array([0.0, 1.0])
    y = np.array([1.0, 0.0])
    assert kalibracio.brier_pontszam(p, y) == pytest.approx(1.0)


def test_brier_bizonytalan_becsles() -> None:
    """Mindig 0.5 → 0.25 Brier (a referenciapont)."""
    p = np.array([0.5, 0.5, 0.5, 0.5])
    y = np.array([1.0, 0.0, 1.0, 0.0])
    assert kalibracio.brier_pontszam(p, y) == pytest.approx(0.25)


def test_brier_eltero_alak() -> None:
    with pytest.raises(ValueError, match="Eltérő alak"):
        kalibracio.brier_pontszam(np.array([0.5]), np.array([1.0, 0.0]))


def test_brier_ures_bemenet() -> None:
    with pytest.raises(ValueError, match="Üres bemenet"):
        kalibracio.brier_pontszam(np.array([]), np.array([]))
