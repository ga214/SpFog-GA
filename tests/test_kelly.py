"""9. lépés — Kelly-tétezés tesztjei.

A specifikáció konkrét példatáblázatát ellenőrizzük: ugyanaz az 5%-os él,
három különböző szorzónál.
"""

from __future__ import annotations

import pytest

from tippmix.tetezes import kelly

# A specifikáció alapértékei
BANKROLL = 50_000
KELLY_HANYAD = 0.25
MIN_FT = 200
MAX_FT = 5_000
MAX_SZAZALEK = 0.04
KEREKITES = 100


def _tet(p: float, odds: float, bankroll: int = BANKROLL) -> int:
    tet, _, _ = kelly.tet_szamitas(
        p, odds, bankroll, KELLY_HANYAD, MIN_FT, MAX_FT, MAX_SZAZALEK, KEREKITES
    )
    return tet


def test_kelly_nyers_keplet() -> None:
    """f* = (p × odds - 1) / (odds - 1)"""
    assert kelly.kelly_nyers(0.5, 3.0) == pytest.approx(0.25)
    assert kelly.kelly_nyers(0.6, 2.0) == pytest.approx(0.2)


def test_kelly_nulla_ha_nincs_el() -> None:
    """Fair áron a Kelly pontosan nulla."""
    assert kelly.kelly_nyers(0.5, 2.0) == pytest.approx(0.0)


def test_kelly_negativ_ha_rossz_az_ar() -> None:
    assert kelly.kelly_nyers(0.4, 2.0) < 0


def test_kelly_ervenytelen_bemenet() -> None:
    with pytest.raises(ValueError, match="p kívül esik"):
        kelly.kelly_nyers(1.5, 2.0)
    with pytest.raises(ValueError, match="Érvénytelen szorzó"):
        kelly.kelly_nyers(0.5, 1.0)


def test_spec_pelda_alacsony_szorzo() -> None:
    """Spec 9. lépés: 1,40-es szorzó, p = 0,764 → f* = 0,174,
    negyed-Kelly 0,0435, tét 2 175 → 2 000 Ft (a 4% plafon vág)."""
    f = kelly.kelly_nyers(0.764, 1.40)
    assert f == pytest.approx(0.174, abs=0.001)

    tet, _f_csillag, f_hasznalt = kelly.tet_szamitas(
        0.764, 1.40, BANKROLL, KELLY_HANYAD, MIN_FT, MAX_FT, MAX_SZAZALEK, KEREKITES
    )
    assert f_hasznalt == pytest.approx(0.0435, abs=0.001)
    # A nyers tét 2 175 lenne, de a 4% plafon = 2 000 Ft vág
    assert tet == 2_000


def test_spec_pelda_kozepes_szorzo() -> None:
    """Spec: 3,50-es szorzó, p = 0,331 → f* = 0,064, tét "800 Ft".

    ELTÉRÉS A SPECIFIKÁCIÓTÓL: a spec 800 Ft-ot ír, a kód 700-at ad.
    A spec a kerekített f* = 0,064 értékkel számolt (0,064 × 0,25 × 50 000
    = 800), a kód a pontos f* = 0,06357-tel (→ 794,6 Ft → lefelé kerekítve
    700). A kód követi a spec 7. pontját ("kerekítés 100 Ft-ra lefelé"),
    a példatáblázat csak illusztráció.
    Lásd: docs/OPEN_QUESTIONS.md — NY-07.
    """
    f = kelly.kelly_nyers(0.331, 3.50)
    assert f == pytest.approx(0.064, abs=0.001)
    assert _tet(0.331, 3.50) == 700


def test_spec_pelda_magas_szorzo() -> None:
    """Spec: 6,00-os szorzó, p = 0,197 → f* = 0,036, tét "455 → 500 Ft".

    ELTÉRÉS A SPECIFIKÁCIÓTÓL: a spec példatáblázata 455-öt FELfelé kerekít
    500-ra, de a spec 7. pontja azt írja: "Kerekítés 100 Ft-ra LEFELÉ", és
    a 6. pont indoklása szerint a felkerekítés felültetéléshez vezet.
    A normatív szabály (lefelé) nyer a példatáblázattal szemben → 400 Ft.
    Lásd: docs/OPEN_QUESTIONS.md — NY-07.
    """
    f = kelly.kelly_nyers(0.197, 6.00)
    assert f == pytest.approx(0.036, abs=0.001)
    assert _tet(0.197, 6.00) == 400


def test_azonos_el_alacsonyabb_szorzonal_nagyobb_tet() -> None:
    """A lényeg: ugyanaz az él alacsony szorzónál nagyobb tétet indokol.

    "egy 1,4-es eseményre többet teszek, mint egy 10-esre"
    """
    assert _tet(0.764, 1.40) > _tet(0.331, 3.50) > _tet(0.197, 6.00)


def test_tul_kis_tet_kiesik() -> None:
    """Ha a tét a min_ft (200) alá esne, a tipp KIESIK. NEM kerekítünk fel."""
    # Nagyon kis él, magas szorzó → nagyon kis tét
    tet = _tet(0.205, 5.00)
    # 0.205*5-1 = 0.025, /4 = 0.00625, *0.25 = 0.0015625, *50000 = 78 Ft
    assert tet == 0


def test_plafon_a_szigorubb_ertek() -> None:
    """A max_ft és a bankroll-százalék közül a szigorúbb nyer."""
    # 50 000 Ft bankrollnál a 4% = 2 000 Ft < 5 000 Ft max_ft
    assert _tet(0.95, 1.20) == 2_000

    # Nagy bankrollnál viszont a max_ft vág: 200 000 × 4% = 8 000 > 5 000
    assert _tet(0.95, 1.20, bankroll=200_000) == 5_000


def test_kerekites_lefele() -> None:
    """A kerekítés mindig lefelé történik."""
    tet, _, _ = kelly.tet_szamitas(0.55, 2.00, 100_000, 0.25, 200, 50_000, 1.0, 100)
    # f* = (0.55*2-1)/1 = 0.1, negyed = 0.025, ×100 000 = 2 500
    assert tet == 2_500
    assert tet % 100 == 0


def test_lehetseges_nyeremeny() -> None:
    assert kelly.lehetseges_nyeremeny(1_500, 1.85) == 2_775
    assert kelly.lehetseges_nyeremeny(400, 3.42) == 1_368


def test_napi_limit_nem_valtoztat_ha_belefer() -> None:
    tetek = [1_000, 800, 600]
    assert kelly.napi_limit_alkalmazas(tetek, 5_000, 200, 100) == tetek


def test_napi_limit_aranyosan_csokkent() -> None:
    """Ha az összeg túllépi a limitet, arányosan csökkentünk."""
    tetek = [4_000, 3_000, 3_000]  # összesen 10 000
    eredmeny = kelly.napi_limit_alkalmazas(tetek, 5_000, 200, 100)
    assert sum(eredmeny) <= 5_000
    # Az arányok nagyjából megmaradnak
    assert eredmeny[0] > eredmeny[1]


def test_napi_limit_kihagyja_a_tul_kicsit() -> None:
    """Ha valamelyik a csökkentés után 200 Ft alá esik, azt kihagyjuk."""
    tetek = [10_000, 300]
    eredmeny = kelly.napi_limit_alkalmazas(tetek, 2_000, 200, 100)
    assert sum(eredmeny) <= 2_000
    # A 300-as tétel a csökkentés után 200 alá esne → kimarad
    assert eredmeny[1] == 0


def test_napi_limit_ures_lista() -> None:
    assert kelly.napi_limit_alkalmazas([], 5_000, 200, 100) == []
