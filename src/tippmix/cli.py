"""Parancssori felület.

Használat:

    tippmix futtat --tipus este           # egy teljes napi futás
    tippmix futtat --szarazon --smoke     # smoke-futás, e-mail és DB nélkül
    tippmix kapcsolat-teszt               # Supabase-kapcsolat ellenőrzése
    tippmix config-ellenorzes             # a YAML-ok validálása
    tippmix zaro-odds                     # a záró szorzók begyűjtése (12. lépés)

A GitHub Actions workflow-k ezeket hívják.
"""

from __future__ import annotations

import argparse
import json
import sys

from tippmix.kozos.config import beallitasok, ligak
from tippmix.kozos.hibak import TippmixHiba
from tippmix.kozos.ido import cet_ido_ma_utc_ban, helyes_idoben_fut, most_utc
from tippmix.kozos.naplo import beallit, naplo

log = naplo(__name__)


def _naplozas_inditas() -> None:
    beall = beallitasok()
    beallit(
        szint=beall.naplozas.szint,
        formatum=beall.naplozas.formatum,
        fajl_konyvtar=beall.naplozas.fajl_konyvtar,
    )


def parancs_futtat(argumentumok: argparse.Namespace) -> int:
    """Egy napi futás."""
    from tippmix.pipeline import FutasOpciok, futtat

    _naplozas_inditas()
    beall = beallitasok()

    # A GitHub Actions cron UTC-ben fut, a DST miatt két bejegyzéssel.
    # Csak az fut végig, amelyik a helyes CET-időben van.
    if argumentumok.ido_ellenorzes:
        cel = beall.futás.délelőtt_cet if argumentumok.tipus == "delelott" else beall.futás.este_cet
        if not helyes_idoben_fut(cel, beall.ido.cron_turés_perc):
            log.info(
                "futas_kihagyva_rossz_idoben",
                cel_cet=cel,
                cel_utc=cet_ido_ma_utc_ban(cel).isoformat(),
                most_utc=most_utc().isoformat(),
                ok="a masik cron-bejegyzes fog futni (nyari/teli idoszamitas)",
            )
            return 0

    try:
        futtat(
            FutasOpciok(
                futas_tipusa=argumentumok.tipus,
                szarazon=argumentumok.szarazon,
                csak_smoke=argumentumok.smoke,
            )
        )
    except TippmixHiba as e:
        log.error("futas_hiba", hiba=str(e))
        return 1
    return 0


def parancs_kapcsolat_teszt(_argumentumok: argparse.Namespace) -> int:
    """Supabase-kapcsolat és séma ellenőrzése."""
    from tippmix.adattar.supabase_kliens import kapcsolat_teszt

    _naplozas_inditas()
    try:
        eredmeny = kapcsolat_teszt()
    except TippmixHiba as e:
        print(f"HIBA: {e}", file=sys.stderr)
        return 1

    print(json.dumps(eredmeny, indent=2, ensure_ascii=False))

    if eredmeny["sema_kesz"]:
        print("\nA séma rendben van. Minden tábla elérhető.")
        return 0

    print(
        f"\nHIÁNYZÓ TÁBLÁK: {', '.join(eredmeny['hianyzo_tablak'])}\n"
        f"Futtasd le a db/migrations/001_init.sql fájlt a Supabase "
        f"SQL Editorában. Lásd: docs/SUPABASE_SETUP.md",
        file=sys.stderr,
    )
    return 1


def parancs_config_ellenorzes(_argumentumok: argparse.Namespace) -> int:
    """A YAML-konfigurációk betöltése és validálása."""
    try:
        beall = beallitasok()
        lig = ligak()
    except TippmixHiba as e:
        print(f"KONFIGURÁCIÓS HIBA:\n{e}", file=sys.stderr)
        return 1

    print("A konfiguráció érvényes.\n")
    print(f"  Bankroll:            {beall.bankroll.aktuális_ft:,} Ft".replace(",", " "))
    print(f"  Tétplafon (szigorúbb): {beall.tet_plafon_ft():,} Ft".replace(",", " "))
    print(f"  min_edge délelőtt:   {beall.küszöb.min_edge_délelőtt:.1%}")
    print(f"  min_edge este:       {beall.küszöb.min_edge_este:.1%}")
    print(f"  Kelly-hányad:        {beall.tét.kelly_hányad}")
    print(f"  Zsugorítás w:        {beall.modell.zsugorítás_w}")
    print()
    print(f"  Aktív futball-ligák: {', '.join(sorted(lig.aktiv_futball_kodok())) or '(nincs)'}")
    print(f"  Aktív kosárligák:    {', '.join(sorted(lig.aktiv_kosar_kodok())) or '(nincs)'}")
    print(f"  Aktív foci-piacok:   {', '.join(sorted(lig.aktiv_piacok('foci')))}")
    print(f"  Aktív kosár-piacok:  {', '.join(sorted(lig.aktiv_piacok('kosar')))}")
    print()
    print(
        f"  Futás délelőtt:      {beall.futás.délelőtt_cet} CET "
        f"= {cet_ido_ma_utc_ban(beall.futás.délelőtt_cet).strftime('%H:%M')} UTC (ma)"
    )
    print(
        f"  Futás este:          {beall.futás.este_cet} CET "
        f"= {cet_ido_ma_utc_ban(beall.futás.este_cet).strftime('%H:%M')} UTC (ma)"
    )
    return 0


def parancs_tortenelmi_letoltes(argumentumok: argparse.Namespace) -> int:
    """Történelmi meccsadat letöltése a modellezéshez (Fázis 1)."""
    _naplozas_inditas()
    from tippmix.gyujtes import tortenelmi

    szezonok = tortenelmi.szezon_kodok(
        argumentumok.szezonok or beallitasok().tortenelmi.szezonok_szama
    )
    print(f"Szezonok: {', '.join(szezonok)}\n")

    try:
        eredmeny = tortenelmi.osszes_aktiv_letoltes(argumentumok.szezonok)
    except TippmixHiba as e:
        print(f"LETÖLTÉSI HIBA:\n{e}", file=sys.stderr)
        return 1

    if not eredmeny:
        print("Egyetlen aktív ligához sincs `soccerdata_liga` a config/ligak.yaml-ban.")
        return 1

    for liga_kod, db in sorted(eredmeny.items()):
        print(f"  {liga_kod:5} {db:6} meccs")
    print(f"\nÖsszesen {sum(eredmeny.values())} meccs.")
    return 0


def parancs_zaro_odds(_argumentumok: argparse.Namespace) -> int:
    """A záró szorzók begyűjtése a CLV-hez (12. lépés)."""
    _naplozas_inditas()
    log.info("zaro_odds_futas_kezdet")
    print("A záró-szorzó gyűjtés még nincs implementálva (Fázis 5).")
    return 0


def main(argv: list[str] | None = None) -> int:
    elemzo = argparse.ArgumentParser(
        prog="tippmix",
        description="Tippmix tipprendszer — automatizált sportfogadási javaslatok",
    )
    alparancsok = elemzo.add_subparsers(dest="parancs", required=True)

    # futtat
    p_futtat = alparancsok.add_parser("futtat", help="egy napi futás")
    p_futtat.add_argument(
        "--tipus",
        choices=["delelott", "este"],
        default=None,
        help="a futás típusa (alapértelmezés: az időpontból számolva)",
    )
    p_futtat.add_argument(
        "--szarazon",
        action="store_true",
        help="nem küld e-mailt és nem ír adatbázisba",
    )
    p_futtat.add_argument(
        "--smoke",
        action="store_true",
        help="smoke-mód: a nem implementált lépéseket átugorja",
    )
    p_futtat.add_argument(
        "--ido-ellenorzes",
        action="store_true",
        help="kilép, ha nem a helyes CET-időben fut (GitHub Actions DST-kezelés)",
    )
    p_futtat.set_defaults(fut=parancs_futtat)

    # kapcsolat-teszt
    p_kapcs = alparancsok.add_parser(
        "kapcsolat-teszt", help="Supabase-kapcsolat és séma ellenőrzése"
    )
    p_kapcs.set_defaults(fut=parancs_kapcsolat_teszt)

    # config-ellenorzes
    p_conf = alparancsok.add_parser("config-ellenorzes", help="a YAML-ok validálása")
    p_conf.set_defaults(fut=parancs_config_ellenorzes)

    # tortenelmi-letoltes
    p_tort = alparancsok.add_parser(
        "tortenelmi-letoltes", help="történelmi meccsadat letöltése a modellezéshez"
    )
    p_tort.add_argument(
        "--szezonok",
        type=int,
        default=None,
        help="hány szezonra visszamenőleg (alapértelmezés a settings.yaml-ból)",
    )
    p_tort.set_defaults(fut=parancs_tortenelmi_letoltes)

    # zaro-odds
    p_zaro = alparancsok.add_parser("zaro-odds", help="záró szorzók begyűjtése a CLV-hez")
    p_zaro.set_defaults(fut=parancs_zaro_odds)

    argumentumok = elemzo.parse_args(argv)
    return int(argumentumok.fut(argumentumok))


if __name__ == "__main__":
    sys.exit(main())
