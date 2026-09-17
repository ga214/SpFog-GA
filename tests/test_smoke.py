"""Smoke-teszt: bizonyítja, hogy a modulok összeállnak.

Ez a teszt nem modellt ellenőriz, hanem azt, hogy:
  - minden modul importálható (nincs körkörös import, nincs elgépelt név)
  - a konfiguráció betölthető és érvényes
  - a pipeline végigfut a vázon
  - a levél összeáll és értelmes szöveget ad

Hálózatot NEM használ, e-mailt NEM küld, adatbázisba NEM ír.
"""

from __future__ import annotations

import importlib

import pytest

from tippmix.kozos.config import beallitasok, ligak
from tippmix.kozos.naplo import beallit
from tippmix.pipeline import FutasOpciok, futtat

# Minden modul, aminek importálhatónak kell lennie
MODULOK = [
    "tippmix",
    "tippmix.cli",
    "tippmix.pipeline",
    "tippmix.kozos.config",
    "tippmix.kozos.hibak",
    "tippmix.kozos.ido",
    "tippmix.kozos.naplo",
    "tippmix.kozos.tipusok",
    "tippmix.kozos.titkok",
    "tippmix.gyujtes.tippmix_scraper",
    "tippmix.gyujtes.tortenelmi",
    "tippmix.illesztes.nevillesztes",
    "tippmix.jellemzok.epito",
    "tippmix.modellek.futball",
    "tippmix.modellek.kosar",
    "tippmix.modellek.kalibracio",
    "tippmix.dontes.vig",
    "tippmix.dontes.dontesi_fa",
    "tippmix.dontes.hirveto",
    "tippmix.tetezes.kelly",
    "tippmix.tetezes.kombinacio",
    "tippmix.kimenet.email_kuldo",
    "tippmix.kimenet.level_formazo",
    "tippmix.adattar.supabase_kliens",
    "tippmix.adattar.naplozo",
    "tippmix.backteszt.keret",
]


@pytest.mark.smoke
@pytest.mark.parametrize("modul_nev", MODULOK)
def test_minden_modul_importalhato(modul_nev: str) -> None:
    """Minden modul importálható — nincs körkörös import vagy elgépelt név."""
    importlib.import_module(modul_nev)


@pytest.mark.smoke
def test_settings_yaml_ervenyes() -> None:
    """A settings.yaml betölthető és megfelel a sémának."""
    beall = beallitasok()

    # A specifikáció konkrét értékei
    assert beall.bankroll.induló_ft == 50_000
    assert beall.tét.kelly_hányad == 0.25
    assert beall.tét.min_ft == 200
    assert beall.tét.max_ft == 5_000
    assert beall.küszöb.min_edge_délelőtt == 0.05
    assert beall.küszöb.min_edge_este == 0.035
    assert beall.modell.zsugorítás_w == 0.35
    assert beall.kombináció.max_láb == 3
    assert beall.futás.min_perc_kezdésig == 45


@pytest.mark.smoke
def test_tetplafon_a_szigorubb() -> None:
    """A max_ft és a bankroll-százalék közül a szigorúbb nyer.

    50 000 Ft bankrollnál a 4% = 2 000 Ft, tehát ez a plafon, nem az 5 000 Ft.
    """
    beall = beallitasok()
    assert beall.tet_plafon_ft() == 2_000


@pytest.mark.smoke
def test_min_edge_napszak_szerint() -> None:
    """Délelőtt magasabb küszöb, mert nincs meg a kezdőcsapat."""
    beall = beallitasok()
    assert beall.min_edge("delelott") > beall.min_edge("este")


@pytest.mark.smoke
def test_ligak_yaml_ervenyes() -> None:
    """A ligak.yaml betölthető, és vannak aktív ligák és piacok."""
    lig = ligak()
    assert "E0" in lig.aktiv_futball_kodok()
    assert "NBA" in lig.aktiv_kosar_kodok()

    # Első verzióban csak 1X2 és OU25 aktív fociban
    foci_piacok = lig.aktiv_piacok("foci")
    assert foci_piacok == {"1X2", "OU25"}
    assert "BTTS" not in foci_piacok  # második kör


@pytest.mark.smoke
def test_pipeline_smoke_futas_vegigmegy() -> None:
    """A pipeline végigfut a vázon, és összeáll a levél.

    EZ A LEGFONTOSABB TESZT ebben a fázisban: bizonyítja, hogy a modulok
    összeállnak és a pipeline nem esik szét az első hívásnál.
    """
    beallit(szint="WARNING", formatum="konzol")

    eredmeny = futtat(FutasOpciok(futas_tipusa="este", szarazon=True, csak_smoke=True))

    assert eredmeny.futas_tipusa == "este"
    assert eredmeny.futas_id
    assert not eredmeny.van_javaslat()  # a váz nem termel javaslatot
    assert any("SMOKE" in f for f in eredmeny.figyelmeztetesek)


@pytest.mark.smoke
def test_level_osszeall_uresen() -> None:
    """A "ma nincs tipp" levél összeáll és informatív.

    "Egy üres levél magyarázat nélkül nyugtalanító; egy üres levél azzal,
    hogy 112 piacot néztem meg, informatív."
    """
    from tippmix.kimenet import level_formazo

    beallit(szint="WARNING", formatum="konzol")
    eredmeny = futtat(FutasOpciok(futas_tipusa="delelott", szarazon=True, csak_smoke=True))

    level = level_formazo.osszeallit(eredmeny)

    assert "nincs tipp" in level.targy
    assert "MA NINCS TIPP" in level.szoveg
    assert "NEM JAVASOLT, DE MEGVIZSGÁLVA" in level.szoveg
    assert eredmeny.futas_id in level.szoveg


@pytest.mark.smoke
def test_cli_config_ellenorzes() -> None:
    """A `tippmix config-ellenorzes` parancs lefut és 0-t ad vissza."""
    from tippmix.cli import main

    assert main(["config-ellenorzes"]) == 0
