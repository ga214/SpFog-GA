"""7. lépés — vig-eltávolítás tesztjei.

Ha a vig-eltávolítás rossz, MINDEN élünk hamis. Ezért ez a modul a
legszigorúbban tesztelt.
"""

from __future__ import annotations

import pytest

from tippmix.dontes import vig


def test_implikalt_valoszinuseg() -> None:
    assert vig.implikalt(2.0) == pytest.approx(0.5)
    assert vig.implikalt(4.0) == pytest.approx(0.25)
    assert vig.implikalt(1.25) == pytest.approx(0.8)


def test_implikalt_ervenytelen_szorzo() -> None:
    with pytest.raises(ValueError, match="Érvénytelen szorzó"):
        vig.implikalt(1.0)
    with pytest.raises(ValueError, match="Érvénytelen szorzó"):
        vig.implikalt(0.5)


def test_overround_pozitiv() -> None:
    """Egy valós 1X2 piac overroundja 5-8% körül van."""
    oddsok = [2.10, 3.40, 3.60]
    o = vig.overround(oddsok)
    assert 0.0 < o < 0.15


def test_aranyos_eltavolitas_osszege_egy() -> None:
    p = vig.aranyos_eltavolitas([2.10, 3.40, 3.60])
    assert sum(p) == pytest.approx(1.0, abs=1e-12)


def test_power_eltavolitas_osszege_egy() -> None:
    """A power módszer lényege: Σ (q_i)^k = 1."""
    p, k = vig.power_eltavolitas([2.10, 3.40, 3.60])
    assert sum(p) == pytest.approx(1.0, abs=1e-9)
    # A k > 1, mert Σ q_i > 1 és minden q_i < 1
    assert k > 1.0


def test_power_es_aranyos_kozel_van_kis_vignel() -> None:
    """Alacsony árrésnél a két módszer közel azonos eredményt ad."""
    # Majdnem fair piac
    eredmeny = vig.vig_eltavolitas([2.02, 2.02])
    assert eredmeny.max_elteres < 0.01


def test_power_nagyobb_valoszinuseget_ad_a_favoritnak() -> None:
    """Favourite-longshot bias: a power módszer a favoritot felértékeli.

    Az irodák a kis esélyű kimenetelekre tesznek arányosan nagyobb árrést,
    ezért az arányos osztás ALULbecsli a favorit fair valószínűségét.

    FONTOS: ez csak POZITÍV overround mellett igaz (k > 1). Negatív
    overroundnál (arbitrázs vagy hibás adat) az irány megfordul — lásd
    test_negativ_overround_figyelmeztet.
    """
    # Valós 1X2 piac, +4.8% overround
    eredmeny = vig.vig_eltavolitas([2.10, 3.40, 3.60])
    assert eredmeny.overround > 0
    assert eredmeny.k_kitevo > 1.0

    favorit_power = eredmeny.p_fair[0]
    favorit_aranyos = eredmeny.p_fair_aranyos[0]
    assert favorit_power > favorit_aranyos

    # És fordítva: a longshot kevesebbet kap a power módszertől
    assert eredmeny.p_fair[2] < eredmeny.p_fair_aranyos[2]


def test_negativ_overround_figyelmeztet() -> None:
    """Negatív overround = arbitrázs vagy hibás adat. Ezt jelezni kell.

    Egy valós fogadóiroda soha nem ad negatív overroundot. Ha mégis ilyet
    látunk, az vagy hiányos kimenetel-lista (a piac egy részét adtuk át), vagy
    elrontott scraping. Csendben átengedni veszélyes: hamis élt gyártana.
    """
    eredmeny = vig.vig_eltavolitas([1.20, 12.00])
    assert eredmeny.overround < 0
    assert eredmeny.gyanus is True
    assert "overround" in eredmeny.gyanu_oka.lower()


def test_valos_piac_nem_gyanus() -> None:
    eredmeny = vig.vig_eltavolitas([2.10, 3.40, 3.60])
    assert eredmeny.gyanus is False


def test_vig_eltavolitas_ket_kimenetel() -> None:
    """Over/under piac: két kimenetel."""
    eredmeny = vig.vig_eltavolitas([1.85, 1.95])
    assert len(eredmeny.p_fair) == 2
    assert sum(eredmeny.p_fair) == pytest.approx(1.0, abs=1e-9)
    assert eredmeny.overround > 0


def test_vig_eltavolitas_egy_kimenetel_hiba() -> None:
    """Egy piac ÖSSZES kimenetelét át kell adni, különben hamis az overround."""
    with pytest.raises(ValueError, match="Legalább 2 kimenetel"):
        vig.vig_eltavolitas([2.0])


def test_edge_szamitas() -> None:
    """A spec 7. lépésének példája: 2,20-as szorzó, p_fair = 0,435,
    a modell 0,48-at mond → edge = 0,045."""
    assert vig.edge(0.48, 0.435) == pytest.approx(0.045, abs=1e-9)


def test_ev_szamitas() -> None:
    """Ugyanaz a példa: EV = 0,48 × 2,20 − 1 = 0,056."""
    assert vig.ev(0.48, 2.20) == pytest.approx(0.056, abs=1e-9)


def test_ev_negativ_ha_nincs_el() -> None:
    """Ha a modell a fair ár alatt van, az EV negatív."""
    assert vig.ev(0.40, 2.20) < 0


def test_referencia_elteres_abszolut() -> None:
    assert vig.referencia_elteres(0.48, 0.534) == pytest.approx(0.054, abs=1e-9)
    assert vig.referencia_elteres(0.534, 0.48) == pytest.approx(0.054, abs=1e-9)


def test_spec_pelda_vegigszamolva() -> None:
    """A specifikáció 7. lépésének teljes példája.

    A Tippmix 2,20-at ad, ebből p_fair = 0,435.
    """
    # A 0,435 egy 1X2 piacból jön; itt a kétkimenetelű közelítést ellenőrizzük:
    # 1/2.20 = 0.4545, a vig levonása után 0.435 körül.
    q = vig.implikalt(2.20)
    assert q == pytest.approx(0.4545, abs=1e-3)
    # A fair ár a nyers implikáltnál kisebb, mert a vig lejön
    eredmeny = vig.vig_eltavolitas([2.20, 1.75])
    assert eredmeny.p_fair[0] < q
