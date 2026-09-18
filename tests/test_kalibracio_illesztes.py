"""A kalibrációs réteg tesztjei (6. lépés, Fázis 3).

Az izotonikus regresszió a modell nyers valószínűségét igazítja ahhoz, amit a
múltban ténylegesen tapasztaltunk: ha a modell "60%"-ot mondott, de az ilyen
esetek 52%-ban jöttek be, a kalibrátor lejjebb húz.

Amit a tesztek védenek: a leképezés monoton maradjon (a sorrendet nem
forgathatja fel), kevés mintánál ne illeszkedjen a zajra, és a kalibrációs
görbe őszintén mutassa meg, ha a modell rosszul van beállítva.
"""

from __future__ import annotations

import numpy as np
import pytest

from tippmix.kozos.hibak import ModellHiba
from tippmix.modellek import kalibracio


def _tulzottan_magabiztos(n: int = 1000, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    """Modell, ami rendszeresen túlbecsüli az esélyeket.

    A becslés 0,1–0,9 között szór, de a tényleges gyakoriság mindig
    alacsonyabb — pontosan az a hiba, amit a kalibrációnak javítania kell.
    """
    rng = np.random.default_rng(seed)
    p_nyers = rng.uniform(0.1, 0.9, n)
    valodi_p = p_nyers * 0.8
    tenyleges = (rng.uniform(size=n) < valodi_p).astype(float)
    return p_nyers, tenyleges


# ---------------------------------------------------------------------------
# Izotonikus illesztés
# ---------------------------------------------------------------------------


def test_izotonikus_javit_a_tulzott_magabiztossagon() -> None:
    p, y = _tulzottan_magabiztos()
    _, eredmeny = kalibracio.izotonikus_illesztes(p, y, "1X2")
    assert eredmeny.brier_utana < eredmeny.brier_elotte
    assert eredmeny.hasznalhato


def test_izotonikus_lehuzza_a_tulbecsult_valoszinuseget() -> None:
    p, y = _tulzottan_magabiztos()
    kalibrator, _ = kalibracio.izotonikus_illesztes(p, y, "1X2")
    assert kalibrator(0.8) < 0.8


def test_izotonikus_monoton_marad() -> None:
    """A kalibráció igazíthat a szinteken, de a SORRENDET nem forgathatja fel."""
    p, y = _tulzottan_magabiztos()
    kalibrator, _ = kalibracio.izotonikus_illesztes(p, y, "1X2")
    ertekek = [kalibrator(x) for x in np.linspace(0.1, 0.9, 30)]
    assert ertekek == sorted(ertekek)


def test_izotonikus_ervenyes_valoszinuseget_ad() -> None:
    p, y = _tulzottan_magabiztos()
    kalibrator, _ = kalibracio.izotonikus_illesztes(p, y, "1X2")
    assert all(0.0 <= kalibrator(x) <= 1.0 for x in (0.0, 0.25, 0.5, 0.75, 1.0))


def test_izotonikus_keves_mintanal_hibat_dob() -> None:
    """Kevés mintából a görbe a zajra illeszkedne — inkább nincs kalibráció."""
    rng = np.random.default_rng(1)
    n = kalibracio.MIN_KALIBRACIOS_MINTA - 1
    with pytest.raises(ModellHiba, match="kevés a kalibrációhoz"):
        kalibracio.izotonikus_illesztes(
            rng.uniform(size=n), rng.integers(0, 2, n).astype(float), "1X2"
        )


def test_izotonikus_eltero_alaknal_hibat_dob() -> None:
    with pytest.raises(ValueError, match="Eltérő alak"):
        kalibracio.izotonikus_illesztes(np.zeros(300), np.zeros(299), "1X2")


def test_izotonikus_rogziti_a_mintaszamot() -> None:
    p, y = _tulzottan_magabiztos(n=500)
    _, eredmeny = kalibracio.izotonikus_illesztes(p, y, "OU25")
    assert eredmeny.minta_db == 500
    assert eredmeny.piac_kod == "OU25"


# ---------------------------------------------------------------------------
# Kalibrációs görbe
# ---------------------------------------------------------------------------


def test_gorbe_jol_kalibralt_modellnel_az_atlot_koveti() -> None:
    rng = np.random.default_rng(3)
    p = rng.uniform(0.05, 0.95, 4000)
    y = (rng.uniform(size=4000) < p).astype(float)
    becsult, tenyleges = kalibracio.kalibracios_gorbe(p, y, kosarak=5)
    assert np.allclose(becsult, tenyleges, atol=0.05)


def test_gorbe_felfedi_a_tulzott_magabiztossagot() -> None:
    """A rosszul kalibrált modellnél a tényleges a becslés ALATT marad."""
    p, y = _tulzottan_magabiztos(n=4000)
    becsult, tenyleges = kalibracio.kalibracios_gorbe(p, y, kosarak=5)
    assert (tenyleges < becsult).all()


def test_gorbe_kosarankent_egy_pontot_ad() -> None:
    rng = np.random.default_rng(5)
    p = rng.uniform(size=1000)
    y = (rng.uniform(size=1000) < p).astype(float)
    becsult, _ = kalibracio.kalibracios_gorbe(p, y, kosarak=10)
    assert len(becsult) == 10


def test_gorbe_ures_bemenetnel_ures_eredmeny() -> None:
    becsult, tenyleges = kalibracio.kalibracios_gorbe(np.array([]), np.array([]))
    assert becsult.size == 0
    assert tenyleges.size == 0


def test_gorbe_azonos_becsleseknel_nem_szall_el() -> None:
    """Ha a modell mindenre ugyanazt mondja, a kvantilisek egybeesnek."""
    p = np.full(500, 0.42)
    y = np.concatenate([np.ones(210), np.zeros(290)])
    becsult, tenyleges = kalibracio.kalibracios_gorbe(p, y)
    assert becsult.size >= 1
    assert becsult[0] == pytest.approx(0.42)
    assert tenyleges[0] == pytest.approx(0.42, abs=0.01)


# ---------------------------------------------------------------------------
# Optimális w
# ---------------------------------------------------------------------------


def test_optimalis_w_a_racsbol_valaszt() -> None:
    n = 200
    rng = np.random.default_rng(11)
    p_kal = rng.uniform(0.3, 0.7, n)
    p_fair = rng.uniform(0.3, 0.7, n)
    odds = 1.0 / p_fair
    zaro = odds * 0.97
    w = kalibracio.optimalis_w(p_kal, p_fair, odds, zaro)
    assert 0.0 <= w <= 1.0


def test_optimalis_w_a_jobb_clvt_valasztja() -> None:
    """Ahol a modell jó, a nagyobb modell-súly (kisebb zsugorítás) nyer."""
    n = 300
    rng = np.random.default_rng(13)
    p_fair = rng.uniform(0.35, 0.65, n)
    # A modell mindig a piac fölé tesz, és a záró ár is felénk mozdul.
    p_kal = np.clip(p_fair + 0.05, 0, 1)
    odds = 1.0 / p_fair
    zaro = odds * 0.90
    w = kalibracio.optimalis_w(p_kal, p_fair, odds, zaro, w_racs=np.array([0.0, 0.5, 1.0]))
    assert w > 0.0
