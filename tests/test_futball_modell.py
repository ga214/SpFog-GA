"""4. lépés — a Dixon-Coles futballmodell tesztjei.

Ez a projekt matematikai magja: ha a modell rossz valószínűséget ad, minden
ráépülő él hamis. Ezért a tesztek a matematikai tulajdonságokat ellenőrzik
(normáltság, szimmetria, monotonitás), nem konkrét számokat — utóbbiak a
ξ és ρ hangolásával változni fognak.

A jövőbe látás elleni védelem külön hangsúlyt kap: ha a `_tanito_halmaz`
beenged egy jövőbeli meccset, a backteszt csodálatos eredményt ad, élesben
meg buksz.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from tippmix.kozos.hibak import ModellHiba
from tippmix.modellek import futball

# ---------------------------------------------------------------------------
# τ — a Dixon-Coles korrekció
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("x", "y"), [(0, 2), (2, 0), (2, 2), (3, 1), (5, 4)])
def test_tau_csak_a_negy_alacsony_cellat_erinti(x: int, y: int) -> None:
    assert futball.tau(x, y, 1.5, 1.2, -0.13) == 1.0


def test_tau_nulla_rho_eseten_semleges() -> None:
    """ρ = 0 mellett a Dixon-Coles visszaesik tiszta Poissonra."""
    for x, y in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        assert futball.tau(x, y, 1.5, 1.2, 0.0) == pytest.approx(1.0)


def test_tau_negativ_rho_noveli_a_dontetleneket() -> None:
    """A negatív ρ felhúzza a 0-0 és 1-1 valószínűségét — ez a korrekció célja."""
    rho = -0.13
    assert futball.tau(0, 0, 1.5, 1.2, rho) > 1.0
    assert futball.tau(1, 1, 1.5, 1.2, rho) > 1.0
    assert futball.tau(0, 1, 1.5, 1.2, rho) < 1.0
    assert futball.tau(1, 0, 1.5, 1.2, rho) < 1.0


# ---------------------------------------------------------------------------
# Idősúlyozás — jövőbe látás elleni védelem
# ---------------------------------------------------------------------------


def test_idosuly_aznapi_meccs_teljes_suly() -> None:
    most = datetime(2026, 9, 1, tzinfo=UTC)
    assert futball.idosuly(most, most, 0.0035) == pytest.approx(1.0)


def test_idosuly_fel_ev_alatt_felez() -> None:
    """ξ = 0.0035 kb. fél év alatt felezi a súlyt (spec 4. lépés)."""
    most = datetime(2026, 9, 1, tzinfo=UTC)
    felezes = futball.idosuly(most - timedelta(days=198), most, 0.0035)
    assert felezes == pytest.approx(0.5, abs=0.01)


def test_idosuly_csokken_az_idovel() -> None:
    most = datetime(2026, 9, 1, tzinfo=UTC)
    sulyok = [futball.idosuly(most - timedelta(days=n), most, 0.0035) for n in (0, 30, 180, 365)]
    assert sulyok == sorted(sulyok, reverse=True)


def test_idosuly_jovobeli_meccs_nulla() -> None:
    """A jövőbeli meccs súlya 0 — a jövőbe látás utolsó védvonala."""
    most = datetime(2026, 9, 1, tzinfo=UTC)
    assert futball.idosuly(most + timedelta(days=1), most, 0.0035) == 0.0


def test_idosuly_naiv_datumot_utcnek_tekint() -> None:
    """A Parquet naiv dátumokat tárol; ez nem dobhat TypeError-t."""
    most = datetime(2026, 9, 1, tzinfo=UTC)
    assert futball.idosuly(datetime(2026, 8, 1), most, 0.0035) > 0


# ---------------------------------------------------------------------------
# Eredménymátrix
# ---------------------------------------------------------------------------


def test_eredmenymatrix_egyre_normalt() -> None:
    m = futball.eredmenymatrix(1.5, 1.2, -0.13)
    assert m.sum() == pytest.approx(1.0)
    assert m.shape == (futball.MATRIX_MERET, futball.MATRIX_MERET)


def test_eredmenymatrix_nem_negativ() -> None:
    assert (futball.eredmenymatrix(1.5, 1.2, -0.13) >= 0).all()


def test_eredmenymatrix_azonos_lambdanal_szimmetrikus() -> None:
    """Egyforma erős csapatoknál a mátrixnak tükrösnek kell lennie."""
    m = futball.eredmenymatrix(1.4, 1.4, -0.13)
    assert np.allclose(m, m.T)


def test_eredmenymatrix_nagyobb_lambda_tobb_golt_jelent() -> None:
    kevés = futball.eredmenymatrix(0.8, 1.2, -0.13)
    sok = futball.eredmenymatrix(2.5, 1.2, -0.13)
    golok = np.arange(futball.MATRIX_MERET)
    assert (sok.sum(axis=1) * golok).sum() > (kevés.sum(axis=1) * golok).sum()


# ---------------------------------------------------------------------------
# Piaci valószínűségek
# ---------------------------------------------------------------------------


def _valoszinusegek(lambda_h: float = 1.5, lambda_v: float = 1.2, rho: float = -0.13) -> dict:
    return futball.piac_valoszinusegek(futball.eredmenymatrix(lambda_h, lambda_v, rho))


def test_1x2_egyre_osszegzodik() -> None:
    p = _valoszinusegek()
    assert p["1"] + p["X"] + p["2"] == pytest.approx(1.0)


def test_ou25_egyre_osszegzodik() -> None:
    p = _valoszinusegek()
    assert p["OU25_Tobb"] + p["OU25_Kevesebb"] == pytest.approx(1.0)


def test_btts_egyre_osszegzodik() -> None:
    p = _valoszinusegek()
    assert p["BTTS_Igen"] + p["BTTS_Nem"] == pytest.approx(1.0)


def test_erosebb_hazai_nagyobb_hazai_eselyt_kap() -> None:
    gyenge = _valoszinusegek(1.0, 1.5)
    eros = _valoszinusegek(2.5, 1.0)
    assert eros["1"] > gyenge["1"]
    assert eros["2"] < gyenge["2"]


def test_azonos_lambda_eseten_kiegyenlitett_1x2() -> None:
    p = _valoszinusegek(1.4, 1.4)
    assert p["1"] == pytest.approx(p["2"], abs=1e-9)


def test_magasabb_lambda_tobb_golt_valoszinusit() -> None:
    assert _valoszinusegek(2.2, 2.0)["OU25_Tobb"] > _valoszinusegek(0.7, 0.6)["OU25_Tobb"]


# ---------------------------------------------------------------------------
# Illesztés
# ---------------------------------------------------------------------------


def _meccsek(napok: int = 200, csapatok: tuple[str, ...] = ("A", "B", "C", "D")) -> pd.DataFrame:
    """Szintetikus liga: az "A" erős, a "D" gyenge."""
    rng = np.random.default_rng(42)
    ero = {"A": 1.0, "B": 0.4, "C": 0.0, "D": -0.6}
    sorok = []
    kezdet = datetime(2026, 1, 1)
    for i in range(napok):
        h, v = rng.choice(csapatok, size=2, replace=False)
        lh = float(np.exp(ero[h] - ero[v] * 0.5 + 0.2))
        lv = float(np.exp(ero[v] - ero[h] * 0.5))
        sorok.append(
            {
                "datum": kezdet + timedelta(days=i),
                "hazai": h,
                "vendeg": v,
                "hazai_gol": int(rng.poisson(lh)),
                "vendeg_gol": int(rng.poisson(lv)),
            }
        )
    return pd.DataFrame(sorok)


def test_illesztes_konvergal_es_felismeri_az_erossorrendet() -> None:
    par = futball.illeszt(_meccsek(), "TESZT", datetime(2026, 9, 1, tzinfo=UTC), xi=0.0035)
    assert par.konvergalt
    assert par.tamadas["A"] > par.tamadas["D"]
    assert par.hazai_elony > 0


def test_illesztes_kizarja_a_jovobeli_meccseket() -> None:
    """A KRITIKUS teszt: az asof utáni meccs nem kerülhet a tanítóhalmazba."""
    meccsek = _meccsek()
    asof = datetime(2026, 3, 1, tzinfo=UTC)
    tanito = futball._tanito_halmaz(meccsek, asof)
    assert len(tanito) < len(meccsek)
    assert (pd.to_datetime(tanito["datum"]) < pd.Timestamp("2026-03-01")).all()


def test_illesztes_asof_elotti_meccsek_szamat_hasznalja() -> None:
    par = futball.illeszt(_meccsek(), "TESZT", datetime(2026, 3, 1, tzinfo=UTC), xi=0.0035)
    assert par.tanito_meccs_db == 59  # 2026-01-01-től 2026-02-28-ig


def test_illesztes_ures_halmaznal_hibat_dob() -> None:
    with pytest.raises(ModellHiba, match="nincs egyetlen meccs"):
        futball.illeszt(_meccsek(), "TESZT", datetime(2025, 1, 1, tzinfo=UTC), xi=0.0035)


def test_illesztes_hianyos_eredmenyt_kihagy() -> None:
    meccsek = _meccsek()
    meccsek.loc[0, "hazai_gol"] = None
    par = futball.illeszt(meccsek, "TESZT", datetime(2026, 9, 1, tzinfo=UTC), xi=0.0035)
    assert par.tanito_meccs_db == len(meccsek) - 1


def test_illesztes_parameterei_a_hataron_belul() -> None:
    """A korlát véd a "soha nem kap gólt" típusú elszabadult becsléstől."""
    par = futball.illeszt(_meccsek(), "TESZT", datetime(2026, 9, 1, tzinfo=UTC), xi=0.0035)
    also, felso = futball._EROSSEG_HATAR
    assert all(also <= v <= felso for v in par.tamadas.values())
    assert all(also <= v <= felso for v in par.vedelem.values())


# ---------------------------------------------------------------------------
# λ-számítás és adatelégségesség
# ---------------------------------------------------------------------------


def test_lambdak_erosebb_hazainak_nagyobb() -> None:
    par = futball.illeszt(_meccsek(), "TESZT", datetime(2026, 9, 1, tzinfo=UTC), xi=0.0035)
    eros_lh, _ = futball.lambdak(par, "A", "D")
    gyenge_lh, _ = futball.lambdak(par, "D", "A")
    assert eros_lh > gyenge_lh


def test_lambdak_ismeretlen_csapatnal_hibat_dob() -> None:
    par = futball.illeszt(_meccsek(), "TESZT", datetime(2026, 9, 1, tzinfo=UTC), xi=0.0035)
    with pytest.raises(ModellHiba, match="ismeretlen csapat"):
        futball.lambdak(par, "A", "NINCS_ILYEN")


def test_meccs_szamok_csak_az_asof_elottieket_szamolja() -> None:
    meccsek = _meccsek()
    szamok = futball.meccs_szamok(meccsek, datetime(2026, 3, 1, tzinfo=UTC))
    assert sum(szamok.values()) == 2 * 59  # meccsenként két csapat


def test_meccs_szamok_a_keves_adatot_lathatova_teszi() -> None:
    """Ez táplálja a 8. lépés KEVES_ADAT kapuját."""
    szamok = futball.meccs_szamok(_meccsek(), datetime(2026, 1, 10, tzinfo=UTC))
    assert all(db < 12 for db in szamok.values())


def test_kor_nap_szamitas() -> None:
    par = futball.illeszt(_meccsek(), "TESZT", datetime(2026, 9, 1, tzinfo=UTC), xi=0.0035)
    assert par.kor_nap(datetime(2026, 9, 9, tzinfo=UTC)) == pytest.approx(8.0)
