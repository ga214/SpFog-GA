"""Megméri, működik-e a "puha iroda ára vs. sharp iroda fair ára" stratégia.

EZ A KÉRDÉS, AMIT ELDÖNT: a saját modellünk bizonyítottan nem veri a piacot
(lásd a walk-forward backtesztet). A javasolt új megközelítés nem is akarja:
a "modell" maga a sharp piac vig-mentesített ára, és csak ott fogadunk, ahol
a *mi* irodánk ennél érdemben jobb árat ad.

Tippmix-történelmi oddsunk nincs, ezért nem a Tippmixet méri, hanem a
MECHANIZMUST: ha egy puhább iroda ára jobb, mint a Pinnacle vig-mentesített
fair ára, az tényleg pozitív EV, vagy csak zaj?

Két teszt fut:

  A) EGYIDEJŰ — az iroda ZÁRÓ ára a Pinnacle ZÁRÓ fair ára ellen.
     Ez a nehezebb teszt: mindkét ár érett. Azt méri, hogy egy iroda a
     záráskor is hagy-e bent kiaknázható félreárazást.

  B) KORAI — az iroda KORAI ára a Pinnacle KORAI fair ára ellen, majd a
     kiértékelés a Pinnacle ZÁRÓ ára ellen. Ez a valós stratégia: most
     látjuk a Tippmix árát, és az a kérdés, megveri-e azt, ahol a sharp
     piac végül zár. Ez maga a CLV.

Adat: football-data.co.uk 1X2 záró ("C") és korai oszlopok. A "PS" a
Pinnacle — a legélesebb, legalacsonyabb margójú referencia.

Futtatás: az `arres-teszt.yml` workflow. Lokálisan is mehet (a
football-data.co.uk nyilvános sportadat, nem szerencsejáték-platform), de a
fejlesztő céges proxyja blokkolhatja.

A küszöbök itt modul-konstansok, nem a settings.yaml-ból jönnek: ez felderítő
szkript, nem a pipeline. Ha a stratégia élesedik, a küszöb a configba megy.
"""

from __future__ import annotations

import io
import sys

import numpy as np
import pandas as pd
import requests

LIGAK = ["E0", "SP1", "D1", "I1", "F1"]
SZEZONOK = ["2122", "2223", "2324", "2425", "2526"]
URL = "https://www.football-data.co.uk/mmz4281/{sz}/{liga}.csv"

# Irodák, amiknek 1X2 oszlopa van a football-data CSV-ben.
# PS = Pinnacle (a sharp referencia), Max = a mezőny legjobb ára,
# Avg = a mezőny átlaga.
IRODAK = ["B365", "BW", "IW", "WH", "VC", "Max", "Avg"]
SHARP = "PS"

# Az EV-küszöbök, amik mentén szűrünk. EV = odds * p_fair - 1.
KUSZOBOK = [0.00, 0.01, 0.02, 0.03, 0.05, 0.08]

# Odds-sávok a bontáshoz: hol lakik az érték, ha lakik valahol.
SAVOK = [
    (1.0, 2.0, "favorit  <2.0"),
    (2.0, 3.5, "közép  2.0-3.5"),
    (3.5, 6.0, "outsider 3.5-6"),
    (6.0, 1e9, "hosszú    >6.0"),
]

# Ennél kevesebb fogadásból nem mondunk semmit.
MIN_FOGADAS = 30


def letolt() -> pd.DataFrame:
    """A football-data.co.uk CSV-k letöltése és összefűzése."""
    darabok = []
    for liga in LIGAK:
        for sz in SZEZONOK:
            cim = URL.format(sz=sz, liga=liga)
            try:
                valasz = requests.get(cim, timeout=60)
            except Exception as hiba:
                print(f"  ! {liga} {sz}: {hiba}", file=sys.stderr)
                continue
            if valasz.status_code != 200:
                print(f"  ! {liga} {sz}: HTTP {valasz.status_code}", file=sys.stderr)
                continue
            tabla = pd.read_csv(io.StringIO(valasz.content.decode("latin-1")), on_bad_lines="skip")
            tabla["liga"] = liga
            tabla["szezon"] = sz
            darabok.append(tabla)
    if not darabok:
        raise SystemExit("Egyetlen CSV-t sem sikerült letölteni.")
    return pd.concat(darabok, ignore_index=True)


def power_devig(odds: np.ndarray) -> np.ndarray:
    """Vektorizált power vig-eltávolítás: (n, 3) szorzó -> (n, 3) fair valség.

    Ugyanaz a matematika, mint a `tippmix.dontes.vig.power_eltavolitas`, csak
    soronkénti hívás helyett numpy-on, mert itt tízezres nagyságrend fut.
    Keressük a k kitevőt, amire sum((1/odds)^k) == 1.
    """
    q = 1.0 / odds
    also = np.full(len(q), 0.01)
    felso = np.full(len(q), 10.0)
    for _ in range(100):
        k = (also + felso) / 2.0
        tulsok = (q ** k[:, None]).sum(axis=1) > 1.0
        also = np.where(tulsok, k, also)
        felso = np.where(tulsok, felso, k)
    return q ** ((also + felso) / 2.0)[:, None]


def odds_oszlopok(tabla: pd.DataFrame, iroda: str, *, zaro: bool) -> np.ndarray | None:
    """Egy iroda 1X2 oszlopai (n, 3) tömbként, vagy None ha nincs meg."""
    jel = "C" if zaro else ""
    nevek = [f"{iroda}{jel}H", f"{iroda}{jel}D", f"{iroda}{jel}A"]
    if not all(nev in tabla.columns for nev in nevek):
        return None
    return tabla[nevek].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)


def ervenyes_sorok(*tombok: np.ndarray) -> np.ndarray:
    """Azok a sorok, ahol minden megadott odds-tömb hiánytalan és 1.0 feletti."""
    jo = np.ones(len(tombok[0]), dtype=bool)
    for tomb in tombok:
        jo &= np.isfinite(tomb).all(axis=1) & (tomb > 1.0).all(axis=1)
    return jo


def fair_valoszinusegek(odds: np.ndarray) -> np.ndarray:
    """Fair valószínűségek, a hiányos sorokban NaN-nal."""
    ki = np.full_like(odds, np.nan)
    jo = ervenyes_sorok(odds)
    ki[jo] = power_devig(odds[jo])
    return ki


def arres_tabla(tabla: pd.DataFrame) -> None:
    """Melyik iroda mennyi árrést tart bent a záró áron."""
    print("=" * 78)
    print("1. ÁRRÉS (overround) a záró 1X2 áron")
    print("=" * 78)
    print("Ez dönti el, mennyi esélye van bármilyen +EV lábnak: minél nagyobb")
    print("az árrés, annál ritkábban lóg ki egy ár a sharp fair ár fölé.\n")
    for iroda in [SHARP, *IRODAK]:
        odds = odds_oszlopok(tabla, iroda, zaro=True)
        if odds is None:
            continue
        jo = ervenyes_sorok(odds)
        if jo.sum() < MIN_FOGADAS:
            continue
        arres = (1.0 / odds[jo]).sum(axis=1) - 1.0
        jelzo = "  <- sharp referencia" if iroda == SHARP else ""
        print(f"  {iroda:5s}  {arres.mean() * 100:5.2f}%   ({jo.sum():5d} meccs){jelzo}")


def kiertekel(
    cimke: str,
    tabla: pd.DataFrame,
    eredmeny: np.ndarray,
    *,
    zaro_ar: bool,
    valaszto_fair: np.ndarray,
    zaro_fair: np.ndarray,
) -> None:
    """Egy teszt lefuttatása minden irodára és küszöbre."""
    print("\n" + "=" * 78)
    print(cimke)
    print("=" * 78)
    print(
        f"{'iroda':6s} {'küszöb':>7s} {'fogadás':>8s} {'talál':>7s} "
        f"{'ROI':>8s} {'±2SE':>7s} {'CLV+':>7s} {'á.odds':>7s}"
    )
    print("-" * 78)

    for iroda in IRODAK:
        odds = odds_oszlopok(tabla, iroda, zaro=zaro_ar)
        if odds is None:
            continue
        jo = (
            ervenyes_sorok(odds)
            & np.isfinite(valaszto_fair).all(axis=1)
            & np.isfinite(zaro_fair).all(axis=1)
        )
        if jo.sum() < 200:
            continue

        # EV minden kimenetelre az iroda áráról, a sharp fair valséggel.
        ev = odds[jo] * valaszto_fair[jo] - 1.0
        irt = False
        for kuszob in KUSZOBOK:
            sor, oszlop = np.where(ev > kuszob)
            if len(sor) < MIN_FOGADAS:
                continue
            fogadott = odds[jo][sor, oszlop]
            nyert = eredmeny[jo][sor] == oszlop
            profit = np.where(nyert, fogadott - 1.0, -1.0)
            # CLV: a fogadott ár megveri-e a Pinnacle ZÁRÓ fair árát.
            clv = fogadott > 1.0 / zaro_fair[jo][sor, oszlop]
            ketse = 2.0 * profit.std(ddof=1) / np.sqrt(len(profit))
            print(
                f"{iroda:6s} {kuszob * 100:6.0f}% {len(sor):8d} "
                f"{nyert.mean() * 100:6.1f}% {profit.mean() * 100:7.2f}% "
                f"{ketse * 100:6.2f}% {clv.mean() * 100:6.1f}% "
                f"{fogadott.mean():7.2f}"
            )
            irt = True
        if irt:
            print("-" * 78)


def sav_bontas(
    tabla: pd.DataFrame,
    eredmeny: np.ndarray,
    *,
    iroda: str,
    valaszto_fair: np.ndarray,
    kuszob: float,
) -> None:
    """Hol lakik az érték: odds-sávonkénti bontás egy irodára."""
    odds = odds_oszlopok(tabla, iroda, zaro=True)
    if odds is None:
        return
    jo = ervenyes_sorok(odds) & np.isfinite(valaszto_fair).all(axis=1)
    ev = odds[jo] * valaszto_fair[jo] - 1.0
    sor, oszlop = np.where(ev > kuszob)
    fogadott = odds[jo][sor, oszlop]
    nyert = eredmeny[jo][sor] == oszlop
    profit = np.where(nyert, fogadott - 1.0, -1.0)

    print("\n" + "=" * 78)
    print(f"4. HOL LAKIK AZ ÉRTÉK — {iroda}, záró ár, EV > {kuszob * 100:.0f}%")
    print("=" * 78)
    print(f"{'sáv':16s} {'fogadás':>8s} {'ROI':>9s} {'±2SE':>8s}")
    print("-" * 78)
    for also, felso, nev in SAVOK:
        maszk = (fogadott >= also) & (fogadott < felso)
        if maszk.sum() < MIN_FOGADAS:
            print(f"{nev:16s} {maszk.sum():8d}   (túl kevés)")
            continue
        reszprofit = profit[maszk]
        ketse = 2.0 * reszprofit.std(ddof=1) / np.sqrt(len(reszprofit))
        print(f"{nev:16s} {maszk.sum():8d} {reszprofit.mean() * 100:8.2f}% {ketse * 100:7.2f}%")


def main() -> None:
    print("Letöltés a football-data.co.uk-ról...", file=sys.stderr)
    nyers = letolt()
    nyers = nyers[nyers["FTR"].isin(["H", "D", "A"])].reset_index(drop=True)
    eredmeny = nyers["FTR"].map({"H": 0, "D": 1, "A": 2}).to_numpy()
    print(
        f"  {len(nyers)} meccs, {nyers['liga'].nunique()} liga, "
        f"{nyers['szezon'].nunique()} szezon\n",
        file=sys.stderr,
    )

    sharp_zaro = odds_oszlopok(nyers, SHARP, zaro=True)
    sharp_korai = odds_oszlopok(nyers, SHARP, zaro=False)
    if sharp_zaro is None or sharp_korai is None:
        raise SystemExit(f"Nincs {SHARP} oszlop az adatban.")

    zaro_fair = fair_valoszinusegek(sharp_zaro)
    korai_fair = fair_valoszinusegek(sharp_korai)
    print(f"Pinnacle záró árral: {ervenyes_sorok(sharp_zaro).sum()} meccs")
    print(f"Pinnacle korai árral: {ervenyes_sorok(sharp_korai).sum()} meccs\n")

    arres_tabla(nyers)

    kiertekel(
        "2. EGYIDEJŰ TESZT — iroda ZÁRÓ ára vs. Pinnacle ZÁRÓ fair ára",
        nyers,
        eredmeny,
        zaro_ar=True,
        valaszto_fair=zaro_fair,
        zaro_fair=zaro_fair,
    )
    kiertekel(
        "3. KORAI TESZT — iroda KORAI ára vs. Pinnacle KORAI fair ára\n"
        "   (a CLV oszlop a Pinnacle ZÁRÓ ára ellen mér — ez a valós stratégia)",
        nyers,
        eredmeny,
        zaro_ar=False,
        valaszto_fair=korai_fair,
        zaro_fair=zaro_fair,
    )

    sav_bontas(nyers, eredmeny, iroda="B365", valaszto_fair=zaro_fair, kuszob=0.02)


if __name__ == "__main__":
    main()
