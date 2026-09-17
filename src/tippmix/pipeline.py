"""A 12 lépéses pipeline vezérlője.

A lépések SOROSAN futnak, megszakítási pontokkal:
  - ha az 1. lépés nem hoz adatot → nincs futás, hibalevél, kilépés
  - ha a 8. lépés mindent kiszűr → a 9-11. lépés nem fut le, hanem
    "ma nincs tipp" levél megy ki

KÉT NAPI FUTÁS:
  délelőtt (09:00 CET) — kora délutáni meccsek, kezdőcsapatok nélkül,
                         MAGASABB küszöbbel
  este     (18:00 CET) — késői meccsek, megerősített felállásokkal,
                         alacsonyabb küszöbbel

Ugyanaz az esemény csak EGYSZER javasolható: a második futás átugorja, amire
már ment javaslat (DUPLIKATUM).

A jelenlegi állapotban a 2-10. lépés még nincs megírva (NotImplementedError).
A `szarazon=True` módban a pipeline végigfut a megírt részeken és üres
eredményt ad — ezt használja a smoke-teszt annak bizonyítására, hogy a
modulok összeállnak.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from tippmix.kimenet import email_kuldo, level_formazo
from tippmix.kozos.config import beallitasok, ligak
from tippmix.kozos.hibak import AdatgyujtesHiba, TippmixHiba
from tippmix.kozos.ido import futas_tipusa as futas_tipusa_szamit
from tippmix.kozos.ido import most_utc
from tippmix.kozos.naplo import futas_id, lepes_kezdet, lepes_veg, naplo
from tippmix.kozos.tipusok import FutasEredmeny

log = naplo(__name__)


@dataclass(frozen=True, slots=True)
class FutasOpciok:
    """Egy futás paraméterei."""

    futas_tipusa: str | None = None  # None → az időpontból számoljuk
    szarazon: bool = False  # nem küld e-mailt, nem ír adatbázisba
    csak_smoke: bool = False  # a nem implementált lépéseket átugorja


def futtat(opciok: FutasOpciok | None = None) -> FutasEredmeny:
    """Egy teljes napi futás.

    Raises:
        AdatgyujtesHiba: az 1. lépés nem hozott adatot
        TippmixHiba: bármely lépés hibája
    """
    opciok = opciok or FutasOpciok()
    beall = beallitasok()
    _ligak = ligak()
    kezdet = time.monotonic()

    most = most_utc()
    tipus = opciok.futas_tipusa or futas_tipusa_szamit(
        beall.futás.délelőtt_cet, beall.futás.este_cet, most
    )

    eredmeny = FutasEredmeny(futas_id=futas_id(), futas_tipusa=tipus, idopont_utc=most)

    log.info(
        "futas_kezdet",
        futas_tipusa=tipus,
        szarazon=opciok.szarazon,
        csak_smoke=opciok.csak_smoke,
        min_edge=beall.min_edge(tipus),
        bankroll_ft=beall.bankroll.aktuális_ft,
        tet_plafon_ft=beall.tet_plafon_ft(),
        aktiv_futball_ligak=sorted(_ligak.aktiv_futball_kodok()),
        aktiv_kosar_ligak=sorted(_ligak.aktiv_kosar_kodok()),
    )

    try:
        if opciok.csak_smoke:
            _smoke_lepesek(eredmeny)
        else:
            _teljes_lepesek(eredmeny, tipus)

        # --- 11. lépés: e-mail ---
        lepes_kezdet(log, 11, "napi_limitek_es_email")
        level = level_formazo.osszeallit(eredmeny)
        kuldo = email_kuldo.alapertelmezett_kuldo(szarazon=opciok.szarazon)
        kuldo.kuld(level)
        lepes_veg(log, 11, "napi_limitek_es_email", targy=level.targy)

        # --- 12. lépés: naplózás ---
        lepes_kezdet(log, 12, "naplozas")
        if opciok.szarazon:
            log.info("naplozas_kihagyva", ok="szarazon")
        else:
            from tippmix.adattar import naplozo

            allapot = "sikeres" if eredmeny.van_javaslat() else "nincs_tipp"
            naplozo.futas_rogzites(eredmeny, allapot, time.monotonic() - kezdet)
            naplozo.javaslatok_rogzitese(eredmeny)
            naplozo.kiesesek_rogzitese(eredmeny)
        lepes_veg(log, 12, "naplozas")

    except AdatgyujtesHiba as e:
        log.error("adatgyujtes_sikertelen", hiba=str(e))
        if not opciok.szarazon:
            email_kuldo.hibalevel(str(e), eredmeny.futas_id)
        raise

    except TippmixHiba as e:
        log.error("futas_sikertelen", hiba=str(e), tipus=type(e).__name__)
        if not opciok.szarazon:
            email_kuldo.hibalevel(f"{type(e).__name__}: {e}", eredmeny.futas_id)
        raise

    log.info(
        "futas_veg",
        javaslat_db=len(eredmeny.javaslatok),
        kombinacio_db=len(eredmeny.kombinaciok),
        kieses_db=len(eredmeny.kiesesek),
        osszes_tet_ft=eredmeny.osszes_tet_ft(),
        futasido_mp=round(time.monotonic() - kezdet, 2),
    )
    return eredmeny


def _smoke_lepesek(eredmeny: FutasEredmeny) -> None:
    """Smoke-mód: a nem implementált lépéseket átugorja, de naplózza őket.

    Ez bizonyítja, hogy a modulok összeállnak: minden import feloldható,
    minden konfiguráció betölthető, a levél összeáll.
    """
    lepesek = [
        (1, "esemeny_begyujtes"),
        (2, "nevillesztes"),
        (3, "feature_epites"),
        (4, "futballmodell"),
        (5, "kosarmodell"),
        (6, "kalibracio_zsugoritas"),
        (7, "vig_eltavolitas_el"),
        (8, "dontesi_fa"),
        (9, "tetezes"),
        (10, "kombinacio_epites"),
    ]
    for szam, nev in lepesek:
        lepes_kezdet(log, szam, nev)
        lepes_veg(log, szam, nev, allapot="varazs_meg_nincs_implementalva")

    eredmeny.figyelmeztetesek.append(
        "SMOKE-FUTÁS: a 2-10. lépés még nincs implementálva. "
        "Ez a levél a váz működését bizonyítja, nem valódi javaslat."
    )


def _teljes_lepesek(eredmeny: FutasEredmeny, futas_tipusa: str) -> None:
    """A teljes pipeline. A lépések a fejlesztési fázisok szerint épülnek be."""
    from tippmix.dontes import dontesi_fa
    from tippmix.gyujtes import tippmix_scraper
    from tippmix.illesztes import nevillesztes
    from tippmix.tetezes import kombinacio

    # --- 1. lépés ---
    lepes_kezdet(log, 1, "esemeny_begyujtes")
    nyers = tippmix_scraper.letolt()
    eredmeny.megvizsgalt_piac_db = len(nyers)
    lepes_veg(log, 1, "esemeny_begyujtes", nyers_sor_db=len(nyers))

    # --- 2. lépés ---
    lepes_kezdet(log, 2, "nevillesztes")
    esemenyek, ismeretlenek = nevillesztes.illeszt(nyers)
    eredmeny.megvizsgalt_esemeny_db = len(esemenyek)
    eredmeny.ismeretlen_csapatok = [
        (i.tippmix_nev, i.javasolt_kanonikus_id or "", i.fuzzy_pontszam) for i in ismeretlenek
    ]
    lepes_veg(log, 2, "nevillesztes", esemeny_db=len(esemenyek), ismeretlen_db=len(ismeretlenek))

    # --- 3-7. lépés: jelöltek építése ---
    # (feature-építés, modellek, kalibráció, zsugorítás, vig-eltávolítás)
    jeloltek = _jeloltek_epitese(esemenyek)

    # --- 8. lépés ---
    lepes_kezdet(log, 8, "dontesi_fa")
    tulelok, kiesesek = dontesi_fa.szur(jeloltek, futas_tipusa, eredmeny.idopont_utc, set())
    eredmeny.kiesesek = kiesesek
    lepes_veg(log, 8, "dontesi_fa", tulelo_db=len(tulelok), kieses_db=len(kiesesek))

    # Megszakítási pont: ha minden kiesett, a 9-10. lépés nem fut le
    if not tulelok:
        log.info("nincs_tulelo_jelolt", ok="minden_jelolt_kiesett")
        return

    # --- 9. lépés ---
    lepes_kezdet(log, 9, "tetezes")
    eredmeny.javaslatok = _tetezes(tulelok)
    lepes_veg(log, 9, "tetezes", javaslat_db=len(eredmeny.javaslatok))

    # --- 10. lépés ---
    lepes_kezdet(log, 10, "kombinacio_epites")
    eredmeny.kombinaciok = kombinacio.epit(eredmeny.javaslatok)
    lepes_veg(log, 10, "kombinacio_epites", kombinacio_db=len(eredmeny.kombinaciok))


def _jeloltek_epitese(esemenyek: list) -> list:
    """3-7. lépés: jellemzők, modellek, kalibráció, zsugorítás, él."""
    raise NotImplementedError("3-7. lépés — a Fázis 2-4-ben készül el")


def _tetezes(tulelok: list) -> list:
    """9. lépés: Kelly-tétezés + napi limitek."""
    raise NotImplementedError("9. lépés — a Fázis 5-ben készül el")
