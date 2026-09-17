"""11. lépés — A levél összeállítása.

A CÉL: "kinyisd, és pontosan tudd, mit kell beütnöd a Tippmix Pro-ba,
gondolkodás nélkül."

A formátum a specifikáció 11. lépésének példáját követi.

MIÉRT VAN BENNE A "NEM JAVASOLT" RÉSZ? Mert így látod, hogy a rendszer
dolgozott, csak nem talált semmit — nem pedig elromlott. Egy üres levél
magyarázat nélkül nyugtalanító; egy üres levél azzal, hogy "112 piacot
néztem meg, 71-nél túl kicsi volt az él", informatív.

MEGJEGYZÉS: itt keletkezik az EGYETLEN helyi idő a rendszerben. Minden
máshol UTC van.
"""

from __future__ import annotations

from tippmix.kimenet.email_kuldo import Level
from tippmix.kozos.config import beallitasok
from tippmix.kozos.ido import megjelenites
from tippmix.kozos.naplo import naplo
from tippmix.kozos.tipusok import FutasEredmeny, Javaslat, Kombinacio

log = naplo(__name__)

_NAPSZAK = {"delelott": "délelőtt", "este": "este"}


def _ft(osszeg: int) -> str:
    """Forint összeg magyar tagolással: 1500 → "1 500 Ft"."""
    return f"{osszeg:,}".replace(",", " ") + " Ft"


def _szazalek(ertek: float, tizedes: int = 1) -> str:
    return f"{ertek * 100:.{tizedes}f}%"


def _szazalekpont(ertek: float, tizedes: int = 1) -> str:
    elojel = "+" if ertek >= 0 else ""
    return f"{elojel}{ertek * 100:.{tizedes}f} pp"


def targy(eredmeny: FutasEredmeny) -> str:
    """A levél tárgya.

    Példa: "Tippmix javaslatok — 2026-09-17 este — 3 tipp, 3 400 Ft"
    """
    beall = beallitasok()
    nap = megjelenites(eredmeny.idopont_utc, "%Y-%m-%d")
    napszak = _NAPSZAK.get(eredmeny.futas_tipusa, eredmeny.futas_tipusa)
    db = len(eredmeny.javaslatok) + len(eredmeny.kombinaciok)

    if db == 0:
        return f"{beall.email.targy_elotag} — {nap} {napszak} — nincs tipp"

    return (
        f"{beall.email.targy_elotag} — {nap} {napszak} — {db} tipp, {_ft(eredmeny.osszes_tet_ft())}"
    )


def _egyes_blokk(sorszam: int, j: Javaslat) -> list[str]:
    """Egy egyes fogadás blokkja."""
    e = j.esemeny
    jel = j.jelolt
    kezdes = megjelenites(e.kezdes_utc, "%H:%M")

    sorok = [
        f"{sorszam}) {e.hazai_nev} - {e.vendeg_nev}  ({e.liga_kod}, {kezdes})",
        f"   Piac:     {jel.odds.piac_kod} — {jel.odds.kimenetel}"
        + (f" ({jel.odds.vonal})" if jel.odds.vonal is not None else ""),
        f"   Szorzó:   {j.odds:.2f}",
        f"   TÉT:      {_ft(j.tet_ft)}",
        f"   Lehetséges nyeremény: {_ft(j.lehetseges_nyeremeny_ft)}",
        "",
        f"   Modell: {_szazalek(jel.p_vegleges)}  |  "
        f"Piac (vig nélkül): {_szazalek(jel.odds.p_fair or 0.0)}  |  "
        f"Él: {_szazalekpont(jel.edge)}  |  "
        f"EV: {_szazalekpont(jel.ev)}",
    ]

    if jel.indoklas:
        sorok.append(f"   Indok: {jel.indoklas}")

    if jel.referencia_p_fair is not None:
        elteres = abs(jel.p_vegleges - jel.referencia_p_fair)
        sorok.append(
            f"   Ellenőrzés: referencia-piac {_szazalek(jel.referencia_p_fair)} "
            f"(eltérés {elteres * 100:.1f} pp — rendben)"
        )
    else:
        sorok.append("   Ellenőrzés: nem volt referencia-adat")

    hir = {
        "tiszta": "Felállás: megerősítve, nincs kulcshiányzó",
        "veto": "Felállás: VÉTÓ (ez nem kerülhetett volna ide)",
        "nincs_ellenorzes": "Felállás: NEM ELLENŐRIZVE — a küszöb meg lett emelve",
    }.get(jel.hirveto_allapot, "")
    if hir:
        sorok.append(f"   {hir}")

    sorok.append("")
    return sorok


def _kombi_blokk(sorszam: int, k: Kombinacio) -> list[str]:
    """Egy kombináció blokkja."""
    sorok = [
        f"K{sorszam}) {len(k.labak)} lábas kötés — együttes szorzó: {k.kombi_odds:.2f}",
        f"    TÉT: {_ft(k.tet_ft)}   |   Lehetséges nyeremény: {_ft(k.lehetseges_nyeremeny_ft)}",
    ]

    for i, lab in enumerate(k.labak):
        betu = chr(ord("a") + i)
        e = lab.esemeny
        meccs = f"{e.hazai_nev} - {e.vendeg_nev}"
        piac = f"{lab.jelolt.odds.piac_kod} {lab.jelolt.odds.kimenetel}"
        sorok.append(f"    {betu}) {meccs:.<30} {piac:.<24} {lab.odds:.2f}")

    sorok.append(
        f"    Együttes modell-valószínűség: {_szazalek(k.kombi_p)}  |  "
        f"EV: {_szazalekpont(k.kombi_ev)}"
    )
    sorok.append("")
    return sorok


def szoveg(eredmeny: FutasEredmeny) -> str:
    """A levél teljes szövege, a specifikáció 11. lépésének formátumában."""
    beall = beallitasok()
    sorok: list[str] = []

    # --- Egyes fogadások ---
    if eredmeny.javaslatok:
        sorok.append("=== EGYES FOGADÁSOK ===")
        sorok.append("")
        for i, j in enumerate(eredmeny.javaslatok, start=1):
            sorok.extend(_egyes_blokk(i, j))

    # --- Kombinációk ---
    if eredmeny.kombinaciok:
        sorok.append("=== KOMBINÁCIÓ ===")
        sorok.append("")
        for i, k in enumerate(eredmeny.kombinaciok, start=1):
            sorok.extend(_kombi_blokk(i, k))

    # --- Összesítő ---
    if eredmeny.van_javaslat():
        osszes = eredmeny.osszes_tet_ft()
        arany = osszes / beall.bankroll.aktuális_ft if beall.bankroll.aktuális_ft else 0.0
        sorok.append("=== ÖSSZESÍTŐ ===")
        sorok.append(f"Mai összes tét: {_ft(osszes)} (a bankroll {_szazalek(arany)}-a)")
        sorok.append(f"Maximális nyeremény, ha minden bejön: {_ft(eredmeny.max_nyeremeny_ft())}")
        sorok.append("")
    else:
        sorok.append("=== MA NINCS TIPP ===")
        sorok.append("")
        sorok.append("A rendszer végigfutott, de egyetlen jelölt sem ment át a szűrőkön.")
        sorok.append("Ez nem hiba: a piaci zsugorítás és a szigorú küszöbök")
        sorok.append("szándékosan kevés tippet engednek át.")
        sorok.append("")

    # --- Nem javasolt, de megvizsgálva ---
    sorok.append("=== NEM JAVASOLT, DE MEGVIZSGÁLVA ===")
    sorok.append(
        f"{eredmeny.megvizsgalt_esemeny_db} esemény, "
        f"{eredmeny.megvizsgalt_piac_db} piac. Kiesési okok:"
    )
    okok = eredmeny.kiesesek_okonkent()
    if okok:
        # Soronként legfeljebb 3 ok, a spec példájának megfelelően
        tetelek = [f"{ok.value}: {db}" for ok, db in okok.items()]
        for i in range(0, len(tetelek), 3):
            sorok.append("  " + " | ".join(tetelek[i : i + 3]))
    else:
        sorok.append("  (nem volt kiesés)")
    sorok.append("")

    # --- Figyelem ---
    figyelmeztetesek: list[str] = list(eredmeny.figyelmeztetesek)
    for nev, javasolt, pont in eredmeny.ismeretlen_csapatok:
        figyelmeztetesek.append(
            f'Ismeretlen csapatnév: "{nev}" — javasolt: {javasolt or "nincs javaslat"}'
            + (f" (hasonlóság: {pont}%)" if javasolt else "")
        )
    if eredmeny.ismeretlen_csapatok:
        figyelmeztetesek.append("Add hozzá a data/team_aliases.csv fájlhoz.")

    if figyelmeztetesek:
        sorok.append("=== FIGYELEM ===")
        sorok.extend(figyelmeztetesek)
        sorok.append("")

    # --- Lábjegyzet ---
    sorok.append("---")
    sorok.append(f"Futás azonosító: {eredmeny.futas_id}")
    sorok.append(f"Időpont: {megjelenites(eredmeny.idopont_utc, '%Y-%m-%d %H:%M')} (CET)")

    return "\n".join(sorok)


def osszeallit(eredmeny: FutasEredmeny) -> Level:
    """A teljes levél: tárgy + szöveg."""
    return Level(targy=targy(eredmeny), szoveg=szoveg(eredmeny))
