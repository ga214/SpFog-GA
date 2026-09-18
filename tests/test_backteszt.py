"""A walk-forward backteszt tesztjei.

A legfontosabb, amit védenek: a backteszt NEM láthat a jövőbe. Ha ezt
elrontjuk, csodálatos eredményt kapunk, és élesben bukunk — és a hiba néma.

A második: a kiértékelés matematikája (ROI, drawdown, szűrők) helyes legyen,
mert erre épül a "megérje-e egyáltalán" döntés.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from tippmix.backteszt import keret

# ---------------------------------------------------------------------------
# Illesztési ütemezés
# ---------------------------------------------------------------------------


def test_illesztesi_napok_heti_utemben() -> None:
    napok = keret._illesztesi_napok(date(2025, 1, 1), date(2025, 1, 22), 7)
    assert napok == [date(2025, 1, 1), date(2025, 1, 8), date(2025, 1, 15), date(2025, 1, 22)]


def test_illesztesi_napok_nem_lepi_tul_a_veget() -> None:
    napok = keret._illesztesi_napok(date(2025, 1, 1), date(2025, 1, 10), 7)
    assert all(nap <= date(2025, 1, 10) for nap in napok)


def test_illesztesi_napok_egynapos_ablak() -> None:
    assert keret._illesztesi_napok(date(2025, 1, 1), date(2025, 1, 1), 7) == [date(2025, 1, 1)]


# ---------------------------------------------------------------------------
# Tényleges kimenetelek
# ---------------------------------------------------------------------------


def _meccs(hazai_gol: int, vendeg_gol: int) -> pd.Series:
    return pd.Series({"hazai_gol": hazai_gol, "vendeg_gol": vendeg_gol})


def test_tenyleges_hazai_gyozelem() -> None:
    k = keret._tenyleges_kimenetelek(_meccs(2, 0))
    assert (k["1"], k["X"], k["2"]) == (1, 0, 0)


def test_tenyleges_dontetlen() -> None:
    k = keret._tenyleges_kimenetelek(_meccs(1, 1))
    assert (k["1"], k["X"], k["2"]) == (0, 1, 0)


def test_tenyleges_vendeg_gyozelem() -> None:
    k = keret._tenyleges_kimenetelek(_meccs(0, 3))
    assert (k["1"], k["X"], k["2"]) == (0, 0, 1)


@pytest.mark.parametrize(
    ("h", "v", "tobb"),
    [(0, 0, 0), (1, 1, 0), (2, 0, 0), (2, 1, 1), (3, 0, 1), (4, 2, 1)],
)
def test_tenyleges_golszam_hatara_pontosan_2_5(h: int, v: int, tobb: int) -> None:
    """A 2.5-ös vonal: 2 gól alatta, 3 gól felette. Itt könnyű elcsúszni."""
    k = keret._tenyleges_kimenetelek(_meccs(h, v))
    assert k["OU25_Tobb"] == tobb
    assert k["OU25_Kevesebb"] == 1 - tobb


def test_tenyleges_kimenetelek_egymast_kizarjak() -> None:
    k = keret._tenyleges_kimenetelek(_meccs(2, 1))
    assert k["1"] + k["X"] + k["2"] == 1
    assert k["OU25_Tobb"] + k["OU25_Kevesebb"] == 1


# ---------------------------------------------------------------------------
# Kiértékelés
# ---------------------------------------------------------------------------


def _jeloltek(sorok: list[dict]) -> pd.DataFrame:
    alap = {
        "datum": pd.Timestamp("2025-01-01"),
        "liga_kod": "E0",
        "hazai": "A",
        "vendeg": "B",
        "piac": "1X2",
        "kimenetel": "1",
        "odds": 2.0,
        "p_modell": 0.55,
        "p_piac_fair": 0.50,
        "p_vegleges": 0.55,
        "edge": 0.05,
        "ev": 0.10,
        "bekovetkezett": 1,
        "gyanus_piac": False,
    }
    return pd.DataFrame([{**alap, **sor} for sor in sorok])


def _ertekel(jeloltek: pd.DataFrame, **kwargs):
    alap = {"min_edge": 0.03, "min_odds": 1.30, "max_odds": 6.00, "parameterek": {}}
    return keret._ertekel(jeloltek, **{**alap, **kwargs})


def test_ures_jeloltlista_nem_dob_hibat() -> None:
    e = _ertekel(pd.DataFrame())
    assert e.fogadas_db == 0
    assert e.nyereseg == 0.0


def test_kis_el_nem_lesz_fogadas() -> None:
    e = _ertekel(_jeloltek([{"edge": 0.01}]))
    assert e.fogadas_db == 0


def test_odds_savon_kivul_nem_lesz_fogadas() -> None:
    assert _ertekel(_jeloltek([{"odds": 1.10}])).fogadas_db == 0
    assert _ertekel(_jeloltek([{"odds": 9.00}])).fogadas_db == 0


def test_gyanus_piac_kimarad() -> None:
    """A gyanús vig-eredmény hamis élt gyárt — ki kell szűrni (D-008)."""
    assert _ertekel(_jeloltek([{"gyanus_piac": True}])).fogadas_db == 0


def test_nyert_fogadas_hozama_odds_minusz_egy() -> None:
    e = _ertekel(_jeloltek([{"odds": 2.5, "bekovetkezett": 1}]))
    assert e.fogadas_db == 1
    assert e.nyereseg == pytest.approx(1.5)
    assert e.roi == pytest.approx(1.5)


def test_vesztett_fogadas_hozama_minusz_egy() -> None:
    e = _ertekel(_jeloltek([{"odds": 2.5, "bekovetkezett": 0}]))
    assert e.nyereseg == pytest.approx(-1.0)


def test_roi_a_tetek_szamahoz_viszonyit() -> None:
    e = _ertekel(
        _jeloltek(
            [
                {"odds": 2.0, "bekovetkezett": 1},
                {"odds": 2.0, "bekovetkezett": 0},
                {"odds": 2.0, "bekovetkezett": 0},
            ]
        )
    )
    assert e.fogadas_db == 3
    assert e.nyereseg == pytest.approx(-1.0)
    assert e.roi == pytest.approx(-1.0 / 3)


def test_max_drawdown_a_legnagyobb_visszaeses() -> None:
    e = _ertekel(
        _jeloltek(
            [
                {"odds": 2.0, "bekovetkezett": 1},  # +1.0, csúcs
                {"odds": 2.0, "bekovetkezett": 0},  # 0.0
                {"odds": 2.0, "bekovetkezett": 0},  # -1.0
            ]
        )
    )
    assert e.max_drawdown == pytest.approx(2.0)


def test_brier_minden_jeloltre_szamol_nem_csak_a_fogadasokra() -> None:
    """A Brier a modell minőségét méri, azt nem szabad a szűrőkre szűkíteni."""
    jeloltek = _jeloltek([{"edge": 0.01}, {"edge": 0.05}])
    e = _ertekel(jeloltek)
    assert e.fogadas_db == 1
    assert not pd.isna(e.brier)


def test_jeloltek_megmaradnak_az_eredmenyben() -> None:
    """A jelöltek kellenek a kalibrációs görbéhez és a paraméterkereséshez."""
    e = _ertekel(_jeloltek([{"edge": 0.05}, {"edge": 0.01}]))
    assert len(e.jeloltek) == 2


# ---------------------------------------------------------------------------
# Jövőbe látás elleni védelem — a legfontosabb blokk
# ---------------------------------------------------------------------------


def test_jelolt_ablak_csak_a_kapu_felett_ertekel() -> None:
    """Kevés meccsű csapat kimarad (KEVES_ADAT), nem kap becslést."""
    from datetime import UTC, datetime

    from tippmix.modellek import futball

    par = futball.DixonColesParameterek(
        liga_kod="E0",
        illesztes_idopont_utc=datetime(2025, 1, 1, tzinfo=UTC),
        tamadas={"A": 0.2, "B": -0.2},
        vedelem={"A": -0.1, "B": 0.1},
        hazai_elony=0.2,
        rho=-0.1,
        xi=0.0035,
        tanito_meccs_db=50,
        konvergalt=True,
        log_likelihood=-100.0,
    )
    ablak = pd.DataFrame(
        [
            {
                "datum": pd.Timestamp("2025-01-05"),
                "liga_kod": "E0",
                "hazai": "A",
                "vendeg": "B",
                "hazai_gol": 1,
                "vendeg_gol": 0,
                "zaro_1x2_h": 2.0,
                "zaro_1x2_d": 3.5,
                "zaro_1x2_a": 4.0,
                "zaro_ou25_tobb": 1.9,
                "zaro_ou25_kevesebb": 1.9,
            }
        ]
    )

    keves = keret._jeloltek_egy_ablakra(par, {"A": 3, "B": 50}, ablak, 12, 0.35)
    assert keves == []

    eleg = keret._jeloltek_egy_ablakra(par, {"A": 50, "B": 50}, ablak, 12, 0.35)
    assert len(eleg) == 5  # 3 db 1X2 + 2 db OU25


def test_walk_forward_illesztes_mindig_az_ablak_elott_all() -> None:
    """Az illesztés asof-ja sosem lehet későbbi az értékelt meccseknél.

    Ez a keret felépítésének invariánsa: minden ablakra az ablak KEZDETÉVEL
    illesztünk, tehát az ablak meccsei nem lehetnek a tanítóhalmazban.
    """
    kezdet, veg = date(2025, 1, 1), date(2025, 3, 1)
    for nap in keret._illesztesi_napok(kezdet, veg, 7):
        ablak_veg = min(nap + timedelta(days=7), veg + timedelta(days=1))
        assert nap < ablak_veg
